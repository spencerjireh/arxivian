# Scoring Pipeline: Two-Stage Paper Triage and Implementability Scoring

The backbone of the feed pivot (see `proposal.md`). A two-stage pipeline triages new
arXiv submissions and produces an evidence-backed implementability score per paper. This
doc is the implementation blueprint; it is grounded in the existing
`services/agent_service/` scaffolding so the new graph reads as native to the codebase.

**Status:** In progress -- Phase 0 is shipped (the `PaperScoreState` / `DimensionScore` schemas, the v1 rubric + LLM prompts, a labeled golden set, and the DB tables via migration `019`). The Stage 1 triage task and the Stage 2 scoring graph are Phase 1.
**Author:** Spencer Jireh
**Date:** July 2026
**Related:** `proposal.md` (direction pitch), `docs/product/feed-prd.md` (product),
`docs/design/scoring-rubric.md` (the concrete v1 rubric anchors + band scale),
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

**v1 scope note.** v1 ships a **4-dimension rubric** (method clarity, resource feasibility,
data availability, demand) with **zero GitHub dependency**. The **code-gap** dimension --
highest-weighted but also least reliable (unproven recall, aggressive rate limits, stale in
the weekly cache) -- is **deferred to v1.1**, where it debuts as an unweighted evidence chip
and is promoted to a weighted signal only after the `spikes/github-code-gap/` spike proves
recall. See the deferral decision below.

### Decisions resolved during design review

- **Global sub-scores, read-time composite.** The pipeline persists *global*
  per-dimension sub-scores plus evidence. The user-weighted composite and the
  compute-profile feasibility match are computed **at read time**, per user, when a digest
  renders. This resolves the tension between one shared cached ranking and per-user
  personalization (`proposal.md` Open Question 3): you cannot cache a single global order
  *and* personalize by compute profile, but you can cache the sub-scores and do the cheap
  arithmetic per request. `digests` caches a candidate ranking snapshot, not a final
  per-user order.
- **Code gap is deferred to v1.1; v1 ships a 4-dimension rubric.** Code gap (does an
  implementation already exist?) is simultaneously the highest-weighted signal *and* the
  least reliable one: unproven GitHub-search recall, aggressive rate limits, and a
  time-sensitive answer that goes stale in the weekly cache ("no code today, code next
  week"). Anchoring v1's ranking on the riskiest signal is the exact false-authority
  trust-killer this design most guards against. So **v1 scores on the four self-contained /
  low-risk dimensions** (method clarity, resource feasibility, data availability, demand)
  and drops `score_code_gap`, `github_client.py`, and `GithubSearchTool` from v1 scope. Code
  gap returns in **v1.1**, first as an *unweighted* "possible existing implementations, as
  of `<date>`" evidence chip, then promoted to a weighted ranking signal only once the spike
  (`spikes/github-code-gap/`) and real usage prove recall clears the bar. This also means
  v1 has **zero GitHub dependency** and only one soft external API (Semantic Scholar). Do
  not ship any "no existing code" claim in the product until code gap is actually weighted.
- **Only 2 of the (v1) 4 dimensions are LLM calls.** Demand is a Semantic Scholar lookup and
  data availability is largely extraction. Only **method clarity** and **resource
  feasibility** are genuinely LLM-judged. (Code gap, when it lands in v1.1, is a GitHub
  search plus a light match-judge -- see the deferral above.) The two LLM dimensions use a
  stronger model by passing an explicit `model=` override to `generate_structured` -- the
  per-call param already exists on `LiteLLMClient`, but **nothing auto-escalates**;
  `ScoringContext` carries the strong-model id (e.g. `openai/gpt-4o-mini` from the
  allowlist) and the nodes pass it. Everything else stays on the cheap/free default. Caveat:
  the cheap default provider (`nvidia_nim/openai/gpt-oss-120b`) satisfies `response_format`
  via prompt-injected JSON, not native schema-constrained decoding, so structured-score
  reliability on the cheap path must be validated -- another reason the eval gate matters.
  The real throughput bottleneck is external API rate limits (Semantic Scholar in v1;
  GitHub once code gap lands), not tokens.
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
 -> [FAN-OUT: 4 parallel dimension nodes (v1), each writes a DISTINCT state key]
     score_method_clarity      LLM-judged from extracted evidence                (weight: high)
     score_resource_feasibility LLM-judged compute extraction -> normalized      (weight: high)
     score_data_availability   extraction -> gate flag                           (gate)
     score_demand              semantic_scholar tool: citation velocity          (weight: medium)
     [v1.1] score_code_gap     github_search tool: API + light LLM match-judge   (deferred)
 -> [FAN-IN]
 -> compose_and_persist        assemble sub-scores + evidence; persist
                               paper_scores + score_evidence; GLOBAL sub-scores
                               only (no user-weighted composite here)
 -> END
```

`score_code_gap` is drawn dashed above: it is **not in v1** (see the deferral decision).
v1 fans out to four nodes; adding code gap in v1.1 is one more `add_node` + one more edge
pair, no topology change.

Registration mirrors `graph_builder.build_graph` -- `StateGraph(PaperScoreState)`,
`add_node(name, fn)`, `add_edge(START, "fetch_and_extract")`, fan-out via four (v1)
`add_edge("fetch_and_extract", "score_<dim>")` edges (LangGraph runs same-source edges in
parallel), fan-in via four `add_edge("score_<dim>", "compose_and_persist")` edges (the
join node runs once after all complete), `add_edge("compose_and_persist", END)`,
`compile(checkpointer=checkpointer)`.

### Rubric

| Dimension | Ships in | Weight | Signal source | LLM? |
|---|---|---|---|---|
| Method clarity | v1 | High | Pseudocode/algorithm blocks, stated hyperparameters, specified architecture | Yes (stronger model) |
| Resource feasibility | v1 | High | Compute requirements extracted from full text -> normalized | Yes (stronger model) |
| Data availability | v1 | Gate | Public datasets vs. proprietary/clinical; disqualifying if inaccessible | Extraction |
| Demand | v1 | Medium | Citation velocity via Semantic Scholar | No (API) |
| Code gap | **v1.1** | Highest (when weighted) | GitHub code/README search for title + arXiv ID; repo stars/issue health | Light (match judge) |

Full-rubric weights match `proposal.md` Section 5.1. **Code gap is deferred to v1.1** (see
the deferral decision above): in v1 it is absent, then reintroduced as an unweighted
evidence chip before becoming the highest-weighted signal. Because only method clarity and
resource feasibility are stronger-model LLM calls, the per-paper LLM cost in v1 is two
structured calls; the rest are API lookups or cheap extraction.

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
    method_clarity_result: DimensionScore
    resource_feasibility_result: DimensionScore
    data_availability_result: DimensionScore
    demand_result: DimensionScore
    # code_gap_result: DimensionScore   # v1.1 -- added with the github_search node
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
client -- confirmed). **Only the Semantic Scholar client ships in v1**; the GitHub client
is v1.1 (it belongs to the deferred code-gap dimension). They are the highest-value and
highest-risk parts of the build, which is exactly why the riskier one (GitHub) is deferred
behind the spike.

### Clients

- `clients/semantic_scholar_client.py` (**v1**) -- lookup by arXiv ID -> citation count and
  velocity. Backoff-aware + net-new Redis cache (see the pattern note below). S2 is the one
  external API v1 depends on; it is far gentler than GitHub code search.
- `clients/github_client.py` (**v1.1**) -- GitHub code/repo search for arXiv ID, title
  variants, and author repos. Returns hits (repo, stars, last commit, README snippet).
  **Backoff-aware + Redis-cached** -- copy the tenacity `Retry-After`-aware backoff pattern
  from `clients/embeddings_client.py` (`JinaEmbeddingsClient`). Note: that client has the
  backoff/retry pattern but **no cache** -- the Redis cache is net-new here (Redis already
  runs for Celery/RedBeat/checkpointing, so the infrastructure exists; there is just no
  client-side caching pattern in the repo to copy). GitHub code search is aggressively
  rate-limited; caching and backoff are load-bearing, not optional. Efficacy is gated by
  the `spikes/github-code-gap/` spike before this client is built.

### Tools (BaseTool wrappers)

- `SemanticScholarTool` (**v1**) / `GithubSearchTool` (**v1.1**) subclass `BaseTool`
  (`services/agent_service/tools/base.py`): `extends_chunks=False`, implement
  `parameters_schema` + `async execute(...) -> ToolResult`; return
  `ToolResult(success, data={...}, prompt_text=<summary>, tool_name=...)` -- copy the
  `tools/list_papers.py` / `tools/propose_ingest.py` shape. Registration is manual and
  imperative in `AgentContext.__init__` (no auto-discovery), so wire each new tool there
  (and mirror it in `ScoringContext`); add name constants to `tools/constants.py` to match
  convention, though note existing tools hardcode `name` as a class attr rather than
  sourcing it from that module.
- **Why wrap as tools, not just node-local client calls:** the scoped per-paper chat agent
  can then reuse them directly ("is there code for this paper?", "how cited is this?"),
  registered in the chat agent's existing `ToolRegistry`. One implementation, two
  consumers.

---

## Data Model

New tables (shipped in migration `019_add_scoring_tables`; models in `backend/src/models/`):

| Table | Columns (sketch) |
|---|---|
| `paper_scores` | paper FK, rubric version, per-dimension sub-scores, model/version metadata. **No stored composite** -- computed at read time. |
| `score_evidence` | score FK, dimension, extracted span or external result (e.g. GitHub hit), source pointer. First-class records -- powers the auditable UI breakdown. |
| `user_paper_states` | user FK, paper FK, state enum (saved / dismissed / implementing / shipped), repo URL, timestamps. Dismissals with optional reason double as labeled feedback. |
| `digests` | week identifier, category set, cached candidate ranking snapshot (sub-scores, not a per-user order). |

Onboarding profile (categories, compute profile, interest keywords) extends the existing
**`preferences`** JSONB column on the `users` model (`models/user.py`) -- the same blob
`scheduled_tasks.py::daily_ingest_task` already reads as `preferences["arxiv_searches"]`.
It is a column, not a `user_preferences` table; no new table is needed for the profile.

**Store-evidence-not-numbers** is the governing rule: sub-scores and their supporting
spans are first-class, which makes both the UI breakdown trustworthy and the rubric
tunable (reweighting = arithmetic over stored sub-scores, never a re-extraction).

### Code-gap staleness (v1.1)

The "no code found" signal is time-sensitive (no code today, code next week) but the
digest caches it. This is exactly the false-authority failure the design most guards
against -- and the primary reason code gap is **deferred out of v1**. When it lands in
v1.1, `score_evidence` for the code-gap dimension carries an "as of `<date>`" stamp,
surfaced in the UI, it debuts as an unweighted chip, and the dimension is subject to a
re-score/decay policy (open question below).

---

## Evaluation

- **Golden set** of 30-50 hand-labeled papers (implementable or not, and why), maintained
  under the existing eval infrastructure.
- Rubric-accuracy eval runs under the `@pytest.mark.eval` profile in CI, alongside the
  existing 80% coverage gate. Target: >=85% agreement with hand labels on the feasibility
  dimension in v1 (add code-gap agreement in v1.1); must not regress.
- User dismissals tagged "misjudged" flow into the golden set over time.
- **The eval gate is what licenses the cheap models.** Using a small model for the two
  judgment dimensions is safe precisely because the golden set catches drift -- e.g. a
  cluster-scale training paper rated "single-GPU feasible."
- **The golden set is a prerequisite, not a later step.** Because the eval gate is what
  licenses the cheap models, the 30-50 labeled papers must exist before the two LLM
  dimensions can be trusted -- build the labeled set alongside (not after) the pipeline.

### Validation before build (spikes)

Two bets are unproven and cheap to test before any schema is committed:

- **Code-gap recall (highest-weighted, highest-risk).** Whether GitHub search can actually
  find a paper's known implementation is an efficacy question, not a coding question. A
  throwaway spike lives at `spikes/github-code-gap/`: it runs several GitHub Search API
  query strategies over ~20 papers with known repos and reports recall@k per strategy plus
  observed rate-limit behavior. Decision rule: if combined recall@10 on
  papers-with-known-code is materially below the bar (~0.8), the code-gap signal needs
  rethinking before the client and `paper_scores` schema are built. The spike's
  `golden_papers.json` doubles as the seed for the eval golden set above.

---

## Files Summary (future implementation)

| Area | New / changed | Phase |
|---|---|---|
| Tasks | `tasks/triage_tasks.py` (Stage 1), `tasks/score_tasks.py` (Stage 2 driver), `tasks/scheduled_tasks.py` (extend: weekly crawl + `build_digest_task`) | v1 |
| Scoring graph | `services/scoring_service/` (builder, 4 dimension nodes, context), `schemas/scoring_state.py` | v1 |
| Clients | `clients/semantic_scholar_client.py` | v1 |
| Tools | `services/agent_service/tools/semantic_scholar.py`, `tools/constants.py` | v1 |
| Crawl | metadata-only path on `clients/arxiv_client.py` | v1 |
| DB | migrations for `paper_scores`, `score_evidence`, `user_paper_states`, `digests`; extend the `preferences` JSONB on `users` | v1 |
| Lifespan | compile scoring graph in `main.py` alongside `agent_graph` | v1 |
| Code gap | `clients/github_client.py`, `.../tools/github_search.py`, `score_code_gap` node | **v1.1** |

---

## Testing Strategy

- Unit: dimension nodes with mocked `llm_client` / clients (`@pytest.mark.unit`).
- Integration: full scoring graph over a fixture paper against the test DB
  (`@pytest.mark.integration`, port 5433).
- Eval: golden-set rubric accuracy (`@pytest.mark.eval`).
- Clients: `semantic_scholar_client` (v1; `github_client` in v1.1) against recorded
  fixtures with rate-limit/backoff paths exercised.

---

## Risks

| Risk | Mitigation |
|---|---|
| Scoring cost | Stage 1 cheap-model filter; only survivors incur full-text cost; digests cached weekly. |
| False authority | Evidence-first records, golden-set eval gate, dismissal feedback as training signal. **Chief mitigation for the riskiest signal: code gap is deferred out of v1 and debuts unweighted in v1.1.** |
| GitHub search recall (v1.1) | Gated by the `spikes/github-code-gap/` spike before build; search arXiv IDs + title variants + author repos; surface the raw results in evidence so misses are visible. |
| S2 rate limits (v1); GitHub rate limits (v1.1, the real bottleneck) | Net-new Redis cache + backoff from day one (reuse the `embeddings_client.py` backoff pattern; add the cache, which does not yet exist in any client). |
| Code-gap staleness (v1.1) | "As of `<date>`" stamp + re-score/decay policy; unweighted chip first. |
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
