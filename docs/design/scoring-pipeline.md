# Scoring Pipeline: Two-Stage Paper Triage and Implementability Scoring

The backbone of the feed pivot (see `proposal.md`). A two-stage pipeline triages new
arXiv submissions and produces an evidence-backed implementability score per paper. This
doc is the implementation blueprint; it is grounded in the existing
`services/agent_service/` scaffolding so the new graph reads as native to the codebase.

**Status:** Design (blueprint for a later implementation task -- no code shipped yet)
**Author:** Spencer Jireh
**Date:** July 2026
**Related:** `proposal.md` (direction pitch), `docs/product/feed-prd.md` (product),
`docs/design/agent-graph-refactor.md` (the sibling chat graph)

---

## Context

The product pivots from chat-first RAG to a ranked feed of "papers worth implementing."
The scored **paper card** replaces the conversation as the core artifact. That score
comes from this pipeline. The design goals, in priority order:

1. **Trust.** A confidently-wrong score at the top of the feed destroys trust faster than
   no score. Every sub-score must be auditable back to an extracted span or an external
   search result. Store evidence, not just numbers.
2. **Cheapness.** Deep-scoring every daily submission would be expensive. A cheap Stage 1
   filter eliminates the bulk before any full-text cost is incurred.
3. **Tunability.** Reweighting the rubric must be arithmetic over stored sub-scores, never
   a re-run of extraction.

### Decisions resolved during design review

- **Global sub-scores, read-time composite.** The pipeline persists *global*
  per-dimension sub-scores plus evidence. The user-weighted composite and the
  compute-profile feasibility match are computed **at read time**, per user, when a digest
  renders. This resolves the tension between one shared cached ranking and per-user
  personalization (`proposal.md` Open Question 3): you cannot cache a single global order
  *and* personalize by compute profile, but you can cache the sub-scores and do the cheap
  arithmetic per request. `digests` caches a candidate ranking snapshot, not a final
  per-user order.
- **Only 2 of 5 dimensions are LLM calls.** Code gap is a GitHub search, demand is a
  Semantic Scholar lookup, data availability is largely extraction. Only **method
  clarity** and **resource feasibility** are genuinely LLM-judged. Those two route to a
  stronger model via LiteLLM prefix routing; everything else stays on the cheap/free
  model. The real throughput bottleneck is external API rate limits (GitHub, Semantic
  Scholar), not tokens.
- **Stage 1 is a batch task, not a graph.** A single classification call over batched
  abstracts needs no LangGraph. It also must NOT reuse `ingest_papers_task` -- Stage 1
  runs on title + abstract only, via a metadata-only crawl distinct from the
  PDF-download/parse/chunk/embed ingestion path.

---

## Pipeline Topology

```
[Celery Beat, weekly after arXiv backlog clears]
        |
        v
Stage 1: triage_new_papers_task (batch, cheap model, metadata only)
        |  ~500-800 papers/day/category -> ~20-30% survive
        v  (one score_paper_task enqueued per survivor)
Stage 2: score_paper_task -> invokes the scoring graph (full text + external signals)
        |
        v
paper_scores + score_evidence (global sub-scores, persisted)
        |
        v
build_digest_task -> digests (cached candidate ranking snapshot)
        |
        v
[read time] feed renders: user-weighted composite + compute-profile match, per user
```

---

## Stage 1 -- Cheap Triage (Celery batch task, NOT a graph)

New file: `backend/src/tasks/triage_tasks.py::triage_new_papers_task`.

- **Metadata-only crawl.** A new lightweight path on `clients/arxiv_client.py` fetches
  title + abstract + arXiv metadata for the target categories. Distinct from
  `tasks/ingest_tasks.py::ingest_papers_task`, which downloads and parses the PDF. Stage 1
  never touches PDFs.
- **Batched classification.** Abstracts are batched into a single
  `llm_client.generate_structured(response_format=TriageResult)` call on the cheap/free
  model (current default `nvidia_nim/openai/gpt-oss-120b`). Batching multiple abstracts
  per request cuts request count against provider rate limits.
- **Survivors** enqueue one `score_paper_task` each (deterministic task IDs, following the
  `scheduled_tasks.py::daily_ingest_task` pattern: date + category + arXiv ID). Rejects
  are recorded (for eval/audit) and dropped.

```python
class TriageResult(BaseModel):
    arxiv_id: str
    paper_class: Literal["method", "survey", "benchmark", "theory", "position"]
    rough_implementability: int = Field(..., ge=0, le=100)
    keep: bool  # survives to Stage 2
    reasoning: str
```

Expected to eliminate 70-80% of submissions at negligible cost.

---

## Stage 2 -- Deep Scoring (LangGraph fixed fan-out/fan-in DAG)

New package: `backend/src/services/scoring_service/`, mirroring `agent_service/`:

| File | Mirrors | Purpose |
|---|---|---|
| `scoring_graph_builder.py` | `agent_service/graph_builder.py` | `build_scoring_graph(checkpointer=None)` |
| `nodes/` | `agent_service/nodes/` | one node fn per stage/dimension |
| `context.py` | `agent_service/context.py` | `ScoringContext` (deps + tools) |
| `schemas/scoring_state.py` | `schemas/langgraph_state.py` | `PaperScoreState` TypedDict + dimension models |

This is a **fixed DAG**, not an agentic tool-selection loop: every paper takes the same
path, so a deterministic map-reduce is cheaper, testable, and eval-friendly. It is still
a genuine LangGraph orchestration (parallel node execution + join).

### Graph topology

```
START
 -> fetch_and_extract          ensure full text ingested (reuse ingest pipeline);
                               extract candidate evidence spans: pseudocode blocks,
                               compute mentions, dataset mentions
 -> [FAN-OUT: 5 parallel dimension nodes, each writes a DISTINCT state key]
     score_code_gap            github_search tool: API + light LLM match-judge   (weight: highest)
     score_method_clarity      LLM-judged from extracted evidence                (weight: high)
     score_resource_feasibility LLM-judged compute extraction -> normalized      (weight: high)
     score_data_availability   extraction -> gate flag                           (gate)
     score_demand              semantic_scholar tool: citation velocity          (weight: medium)
 -> [FAN-IN]
 -> compose_and_persist        assemble sub-scores + evidence; persist
                               paper_scores + score_evidence; GLOBAL sub-scores
                               only (no user-weighted composite here)
 -> END
```

Registration mirrors `graph_builder.build_graph` -- `StateGraph(PaperScoreState)`,
`add_node(name, fn)`, `add_edge(START, "fetch_and_extract")`, fan-out via five
`add_edge("fetch_and_extract", "score_<dim>")` edges (LangGraph runs same-source edges in
parallel), fan-in via five `add_edge("score_<dim>", "compose_and_persist")` edges (the
join node runs once after all five complete), `add_edge("compose_and_persist", END)`,
`compile(checkpointer=checkpointer)`.

### Rubric (v1)

| Dimension | Weight | Signal source | LLM? |
|---|---|---|---|
| Code gap | Highest | GitHub code/README search for title + arXiv ID; repo stars/issue health | Light (match judge) |
| Method clarity | High | Pseudocode/algorithm blocks, stated hyperparameters, specified architecture | Yes (stronger model) |
| Resource feasibility | High | Compute requirements extracted from full text -> normalized | Yes (stronger model) |
| Data availability | Gate | Public datasets vs. proprietary/clinical; disqualifying if inaccessible | Extraction |
| Demand | Medium | Citation velocity via Semantic Scholar | No (API) |

Weights match `proposal.md` Section 5.1. Because only method clarity and resource
feasibility are stronger-model LLM calls, the per-paper LLM cost is two structured calls;
the rest are API lookups or cheap extraction.

### State schema

`PaperScoreState` is a TypedDict (mirroring `AgentState`). Each parallel dimension writes
a **distinct key**, so the last-write-wins merge (no reducers, matching house style) never
collides. Dimension payloads are Pydantic `BaseModel`s carried in the dict.

```python
class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(..., ge=0, le=100)   # or a gate flag for data availability
    evidence: list[EvidenceSpan]            # quoted spans / external hits, source pointers
    reasoning: str

class PaperScoreState(TypedDict):
    paper_id: str
    arxiv_id: str
    extracted_spans: dict           # pseudocode / compute / dataset candidates
    code_gap_result: DimensionScore
    method_clarity_result: DimensionScore
    resource_feasibility_result: DimensionScore
    data_availability_result: DimensionScore
    demand_result: DimensionScore
    rubric_version: str
```

(Alternative: an `Annotated[list[DimensionScore], operator.add]` accumulator instead of
distinct keys -- rejected for v1 in favor of explicit per-dimension fields, matching the
last-write-wins convention used everywhere but `messages` in `AgentState`.)

### Node convention

Same as `agent_service` nodes: `async def <name>_node(state, config) -> dict` returning a
partial state dict; dependencies pulled from `config["configurable"]["context"]`.
`evaluate_batch_node` is the closest template (short-circuit guards + one
`generate_structured` call). The scoring graph does NOT use `get_stream_writer` or
`stream_mode="custom"` (no token streaming) and needs **no checkpointer** (no HITL
interrupts) -- compile it once in `main.py` lifespan alongside `app.state.agent_graph`.

```python
async def score_method_clarity_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context = config["configurable"]["context"]
    spans = state["extracted_spans"]
    result = await context.llm_client.generate_structured(
        messages=[...],
        response_format=DimensionScore,
        model=context.strong_model,   # stronger model for the 2 judgment dimensions
    )
    return {"method_clarity_result": result}
```

---

## New Clients and Tools

Two external signals do not exist in the codebase today (no GitHub or Semantic Scholar
client -- confirmed). They are the highest-value and highest-risk parts of the build.

### Clients

- `clients/github_client.py` -- GitHub code/repo search for arXiv ID, title variants, and
  author repos. Returns hits (repo, stars, last commit, README snippet). **Redis-cached,
  backoff-aware** -- copy the rate-limit-retry pattern from `clients/embeddings_client.py`
  (`JinaEmbeddingsClient`). GitHub code search is aggressively rate-limited; caching and
  backoff are load-bearing, not optional.
- `clients/semantic_scholar_client.py` -- lookup by arXiv ID -> citation count and
  velocity. Cached similarly.

### Tools (BaseTool wrappers)

- `GithubSearchTool` / `SemanticScholarTool` subclass `BaseTool`
  (`services/agent_service/tools/base.py`): `extends_chunks=False`, implement
  `parameters_schema` + `async execute(...) -> ToolResult`; return
  `ToolResult(success, data={...}, prompt_text=<summary>, tool_name=...)` -- copy the
  `tools/list_papers.py` / `tools/propose_ingest.py` shape. Register names in
  `tools/constants.py`.
- **Why wrap as tools, not just node-local client calls:** the scoped per-paper chat agent
  can then reuse them directly ("is there code for this paper?", "how cited is this?"),
  registered in the chat agent's existing `ToolRegistry`. One implementation, two
  consumers.

---

## Data Model

New tables (Alembic migrations are a later task; sketch only):

| Table | Columns (sketch) |
|---|---|
| `paper_scores` | paper FK, rubric version, per-dimension sub-scores, model/version metadata. **No stored composite** -- computed at read time. |
| `score_evidence` | score FK, dimension, extracted span or external result (e.g. GitHub hit), source pointer. First-class records -- powers the auditable UI breakdown. |
| `user_paper_states` | user FK, paper FK, state enum (saved / dismissed / implementing / shipped), repo URL, timestamps. Dismissals with optional reason double as labeled feedback. |
| `digests` | week identifier, category set, cached candidate ranking snapshot (sub-scores, not a per-user order). |

Onboarding profile (categories, compute profile, interest keywords) extends the existing
**`user_preferences`** JSON already read by `scheduled_tasks.py::daily_ingest_task` -- no
new table needed for the profile.

**Store-evidence-not-numbers** is the governing rule: sub-scores and their supporting
spans are first-class, which makes both the UI breakdown trustworthy and the rubric
tunable (reweighting = arithmetic over stored sub-scores, never a re-extraction).

### Code-gap staleness

The "no code found" signal is time-sensitive (no code today, code next week) but the
digest caches it. This is exactly the false-authority failure the design most guards
against. `score_evidence` for the code-gap dimension carries an "as of `<date>`" stamp,
surfaced in the UI, and the dimension is subject to a re-score/decay policy (open
question below).

---

## Evaluation

- **Golden set** of 30-50 hand-labeled papers (implementable or not, and why), maintained
  under the existing eval infrastructure.
- Rubric-accuracy eval runs under the `@pytest.mark.eval` profile in CI, alongside the
  existing 80% coverage gate. Target: >=85% agreement with hand labels on the feasibility
  and code-gap dimensions; must not regress.
- User dismissals tagged "misjudged" flow into the golden set over time.
- **The eval gate is what licenses the cheap models.** Using a small model for the two
  judgment dimensions is safe precisely because the golden set catches drift -- e.g. a
  cluster-scale training paper rated "single-GPU feasible."

---

## Files Summary (future implementation)

| Area | New / changed |
|---|---|
| Tasks | `tasks/triage_tasks.py` (Stage 1), `tasks/score_tasks.py` (Stage 2 driver), `tasks/scheduled_tasks.py` (extend: weekly crawl + `build_digest_task`) |
| Scoring graph | `services/scoring_service/` (builder, nodes, context), `schemas/scoring_state.py` |
| Clients | `clients/github_client.py`, `clients/semantic_scholar_client.py` |
| Tools | `services/agent_service/tools/github_search.py`, `.../semantic_scholar.py`, `tools/constants.py` |
| Crawl | metadata-only path on `clients/arxiv_client.py` |
| DB | migrations for `paper_scores`, `score_evidence`, `user_paper_states`, `digests`; extend `user_preferences` |
| Lifespan | compile scoring graph in `main.py` alongside `agent_graph` |

---

## Testing Strategy

- Unit: dimension nodes with mocked `llm_client` / clients (`@pytest.mark.unit`).
- Integration: full scoring graph over a fixture paper against the test DB
  (`@pytest.mark.integration`, port 5433).
- Eval: golden-set rubric accuracy (`@pytest.mark.eval`).
- Clients: `github_client` / `semantic_scholar_client` against recorded fixtures with
  rate-limit/backoff paths exercised.

---

## Risks

| Risk | Mitigation |
|---|---|
| Scoring cost | Stage 1 cheap-model filter; only survivors incur full-text cost; digests cached weekly. |
| False authority | Evidence-first records, golden-set eval gate, dismissal feedback as training signal. |
| GitHub search recall | Search arXiv IDs + title variants + author repos; surface the raw results in evidence so misses are visible. |
| GitHub / S2 rate limits (the real bottleneck) | Redis cache + backoff from day one (reuse `embeddings_client.py` pattern). |
| Code-gap staleness | "As of `<date>`" stamp + re-score/decay policy. |
| Cheap-model misjudgment | Route the 2 judgment dimensions to a stronger model; golden-set gate. |

---

## Open Questions

1. Re-score/decay cadence for the time-sensitive code-gap dimension.
2. Stage 1 rules-assisted pre-filter (arXiv metadata heuristics) -- deferred, since cheap
   models make Stage 1 cost negligible; only useful for rate-limit/latency relief.
3. Exact read-time composite formula and how compute-profile buckets (laptop / single GPU
   / cloud) map onto the resource-feasibility sub-score.
4. AGPL implications if the scored index is exposed via a public API later
   (`proposal.md` Open Question 4).
