# Scoring Pipeline: Two-Stage Paper Triage and Implementability Scoring

The backbone of the feed pivot (see `proposal.md`). A two-stage pipeline triages new
arXiv submissions and produces an evidence-backed implementability score per paper. This
doc is the implementation blueprint; it is grounded in the existing
`services/agent_service/` scaffolding so the new graph reads as native to the codebase.

**Status:** Phase 1 shipped and running dark (Stage 1 triage, the Stage 2 scoring graph, `build_digest_task`, the golden-set eval gate). As of 2026-09-19 (SPE-286, rubric **v2**) Stage 2 judgments come from **TypeSafe Jev** instead of gpt-5-nano: each judged dimension is a set of atomic typed questions combined in code, and the stored score is a distribution over levels plus the atomic judgments (migration `020`). Nano remains only in Stage 1 triage. See `docs/design/scoring-rubric.md` for the v2 rubric.
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
and is promoted to a weighted signal only after the code-gap spike (SPE-297 removed the script; seed in `tests/evals/fixtures`) proves
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
  (Phase 4; the throwaway script was removed in SPE-297) and real usage prove recall clears
  the bar. This also means
  v1 has **zero GitHub dependency** and only one soft external API (Semantic Scholar). Do
  not ship any "no existing code" claim in the product until code gap is actually weighted.
- **Judgments are typed, not generated (v2).** Demand is a Semantic Scholar lookup; the
  other three dimensions are **TypeSafe Jev** judgments (System One model: typed answers
  with calibrated probabilities, no text generation). Method clarity is four Nouls combined
  by a Poisson-binomial; resource feasibility is one ordinal Score over five compute tiers;
  data availability is one Choice regrouped into the gate. Code owns candidate finding
  (section split + retrieval probes) and combination; Jev only selects and grades. This
  replaced the v1 design (two gpt-5-nano structured calls + a keyword gate) after the
  2026-08-09 dry run showed nano under-rating famous papers by a band with no usable
  uncertainty, and the `jevexperiments` spike showed Jev's low confidence was informative
  in every observed case. `ScoringContext` carries a `TypeSafeClient`; there is no LLM
  client in Stage 2 and no nano fallback. The throughput bottleneck remains external API
  rate limits (Semantic Scholar, TypeSafe 429s handled by the task retry policy), not tokens
  (~5-15k Jev input tokens per paper).
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
  model (`DEFAULT_LLM_MODEL`, currently `openai/gpt-5-nano`). Batching multiple abstracts
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
     score_method_clarity      Jev: 4 clarity Nouls -> Poisson-binomial level dist  (weight: high)
                               + product attributes (code_released, task_type, model_family)
     score_resource_feasibility Jev: compute_tier Score (5 levels) + 2 aux Nouls     (weight: high)
     score_data_availability   Jev: data_access Choice -> PASS/FAIL gate            (gate)
     score_demand              semantic_scholar client: citation velocity           (weight: medium)
     [v1.1] score_code_gap     github_search tool: API + light match-judge          (deferred)
 -> [FAN-IN]
 -> compose_and_persist        derived 0-100 columns + full distributions (JSONB) +
                               attributes + evidence; persist paper_scores +
                               score_evidence; GLOBAL sub-scores only
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

| Dimension | Ships in | Weight | Signal source | Judge |
|---|---|---|---|---|
| Method clarity | v1 (v2 shape) | High | method + experiments sections, pseudocode spans | Jev: 4 Nouls |
| Resource feasibility | v1 (v2 shape) | High | experiments section, compute spans | Jev: 1 Score + 2 Nouls |
| Data availability | v1 (v2 shape) | Gate | abstract, dataset spans | Jev: 1 Choice |
| Demand | v1 | Medium | Citation velocity via Semantic Scholar | No (API) |
| Code gap | **v1.1** | Highest (when weighted) | GitHub code/README search for title + arXiv ID; repo stars/issue health | Light (match judge) |

Full-rubric weights match `proposal.md` Section 5.1. **Code gap is deferred to v1.1** (see
the deferral decision above): in v1 it is absent, then reintroduced as an unweighted
evidence chip before becoming the highest-weighted signal. Per paper, Stage 2 makes three
Jev requests (one per judged node; the attributes ride on the method-clarity request) and
one Semantic Scholar lookup.

### State schema

`PaperScoreState` is a TypedDict (mirroring `AgentState`). Each parallel dimension writes
**distinct keys** (`<dim>_result`, `<dim>_usage`, plus `attributes_result` on the
method-clarity node), so the last-write-wins merge (no reducers, matching house style)
never collides. Dimension payloads are `DimensionScore` models: `level`, `max_level`,
`expected`, `probabilities`, `confidence`, `judgments`, `evidence`, `reasoning`, with
`derived_score()` producing the 0-100 ranking value. `fetch_and_extract` also writes
`sections` (abstract / method / experiments / appendix headings from `paper.raw_text` via
`utils/section_splitter.py`) and `extracted_spans` (retrieval probes + `code_mentions`).

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
partial state dict; dependencies pulled from `config["configurable"]["context"]`. The
scoring graph does NOT use `get_stream_writer` or `stream_mode="custom"` (no token
streaming) and needs **no checkpointer** (no HITL interrupts) -- it is compiled once per
Celery worker (`tasks/score_tasks.py`).

Failure policy: a TypeSafe rate-limit or connection error is **re-raised** (aborting the
graph so `score_paper_task` retries the paper after `retry_after`); any other error
soft-fails the node to `None` so the rest of the paper still scores.

```python
async def score_data_availability_node(state: PaperScoreState, config: RunnableConfig) -> dict:
    context = config["configurable"]["context"]
    payload = {"abstract": state["sections"]["abstract"],
               "dataset_spans": state["extracted_spans"]["dataset"]}
    result = await context.typesafe_client.ask(
        payload, {"data_access": q.DATA_ACCESS}, request_name="data_availability"
    )
    dimension = combine_data_availability(result.choices["data_access"], q.GATE_PASS_OPTIONS, evidence)
    return {"data_availability_result": dimension, "data_availability_usage": {...}}
```

---

## New Clients and Tools

Stage 2 depends on two external services in v1: Semantic Scholar (demand) and TypeSafe
(the Jev judgments). The GitHub client is v1.1 (it belongs to the deferred code-gap
dimension) and is gated behind the spike.

### Clients

- `clients/typesafe_client.py` (**v2**) -- thin wrapper over `typesafe_sdk`'s
  `AsyncTypeSafeClient.system_one`: one `ask(state, questions, request_name)` per node,
  opening a fresh SDK client per call (Celery runs each task on its own event loop),
  `RetryPolicy(max_retries=2, timeout=None)`, SDK errors mapped to `TypeSafeError` /
  `TypeSafeRateLimitError` (`retry_after` seconds) / `TypeSafeConnectionError`, answers
  normalized into plain dataclasses, `input_tokens` logged per request. Settings:
  `TYPESAFE_API_KEY`, `TYPESAFE_MODEL` (pinned `jev-1.13.0`), `TYPESAFE_TIMEOUT_SECONDS`.
- `clients/semantic_scholar_client.py` (**v1**) -- lookup by arXiv ID -> citation count and
  velocity. Backoff-aware + net-new Redis cache (see the pattern note below). S2 is the one
  external API v1 depends on; it is far gentler than GitHub code search. It runs keyless:
  a Redis slot gate (`SEMANTIC_SCHOLAR_MIN_INTERVAL_MS`) spaces requests across all
  workers so the shared ~1 req/s pool is never burst, a lookup that still 429s soft-fails
  to NULL (the composite renormalizes over the present sub-scores), and the nightly
  `backfill_demand_task` retries NULL rows (SPE-284). Weekly volume (~100 lookups, cached
  7 days) is about 1% of the keyless budget, so no API key is requested.
- `clients/github_client.py` (**v1.1**) -- GitHub code/repo search for arXiv ID, title
  variants, and author repos. Returns hits (repo, stars, last commit, README snippet).
  **Backoff-aware + Redis-cached** -- copy the tenacity `Retry-After`-aware backoff pattern
  from `clients/embeddings_client.py` (`JinaEmbeddingsClient`). Note: that client has the
  backoff/retry pattern but **no cache** -- the Redis cache is net-new here (Redis already
  runs for Celery/RedBeat/rate limiting, so the infrastructure exists; there is just no
  client-side caching pattern in the repo to copy). GitHub code search is aggressively
  rate-limited; caching and backoff are load-bearing, not optional. Efficacy is gated by
  the code-gap spike (SPE-297 removed the script; seed in `tests/evals/fixtures`) before this client is built.

### Tools (BaseTool wrappers)

- `SemanticScholarTool` (**v1**) / `GithubSearchTool` (**v1.1**) subclass `BaseTool`
  (`services/agent_service/tools/base.py`): `extends_chunks=False`, implement
  `parameters_schema` + `async execute(...) -> ToolResult`; return
  `ToolResult(success, data={...}, prompt_text=<summary>, tool_name=...)` -- copy the
  `tools/explore_citations.py` shape. Registration is manual and
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
**`preferences`** JSONB column on the `users` model (`models/user.py`) under its own key,
`preferences["feed_profile"]` (`schemas/users.py::FeedProfile`), next to the
`preferences["arxiv_searches"]` blob `scheduled_tasks.py::daily_ingest_task` reads. It is a
column, not a `user_preferences` table; no new table is needed for the profile.

**Read path (Phase 2, SPE-274):** `services/feed_service/` + `schemas/feed.py`. The digest
row is only the candidate set; every card is rebuilt from the live `papers` / `paper_scores`
/ `user_paper_states` rows (three `IN` batch loads per page). Read-time personalization:
per-user composite weights (`compute_composite`, NULL sub-scores renormalize -- SPE-284),
compute-profile match (`laptop` needs feasibility level >= 3, `single_gpu` >= 2, `cloud`
>= 1), keyword tie-break. The verdict line is a code template over the stored judgments
(task type, model family, compute tier, data access) -- no LLM at read time. Signal chips:
`pseudocode_present` (`algorithm_given`), `public_datasets` (gate PASS and not "not
stated"), `single_gpu` (level >= 2), `code_released` (the authors' own statement; never a
"no code" claim). Dimensions with confidence < 0.5 are flagged, not hidden.

**Paper detail (SPE-276):** `GET /papers/{arxiv_id}/score` returns every dimension's level
distribution, atomic judgments and its `score_evidence` spans (the canonical display source;
`dimensions[*].evidence` is a subset). A paper that is not yet scored is scored on demand:
the endpoint enqueues `score_paper_task` (which ingests the full text itself) behind a Redis
`SET NX` lock keyed on the arXiv id, so repeated polls share one task, and answers 202 until
the score exists. The task releases the lock on completion or hard failure; a rate-limit
retry keeps it. Because digest membership keys on `paper_scores.created_at`, an on-demand
score joins the feed only after the next `build_digest_task`.

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
  throwaway spike (git history: `spikes/github-code-gap/`, removed 2026-09-20 in SPE-297)
  ran several GitHub Search API query strategies over ~20 papers with known repos and
  reported recall@k per strategy plus observed rate-limit behavior. Decision rule: if
  combined recall@10 on papers-with-known-code is materially below the bar (~0.8), the
  code-gap signal needs rethinking before the client is built. The spike's labeled seed
  survives as `backend/tests/evals/fixtures/code_gap_golden_papers.json` and doubles as the
  seed for the eval golden set above.

---

## Files Summary

| Area | Files | Status |
|---|---|---|
| Tasks | `tasks/triage_tasks.py` (Stage 1), `tasks/score_tasks.py` (Stage 2 driver, rate-limit-safe retry policy), `tasks/digest_tasks.py` (`build_digest_task`) | shipped |
| Scoring graph | `services/scoring_service/` (builder, `questions.py`, `judgments.py`, `nodes/`, context), `schemas/scoring_state.py` | shipped (v2) |
| Sections | `utils/section_splitter.py` (heading split, positional fallbacks, code mentions over `paper.raw_text`) | shipped (v2) |
| Clients | `clients/typesafe_client.py`, `clients/semantic_scholar_client.py` | shipped |
| Tools | `services/agent_service/tools/semantic_scholar.py` | shipped |
| DB | migrations `019_add_scoring_tables`, `020_add_score_dimensions` (`dimensions`, `attributes`, `model`, `input_tokens` on `paper_scores`) | shipped |
| Eval | `tests/evals/integration/test_scoring_eval.py` (implementable gate + calibration report), `tests/evals/fixtures/scoring_scenarios.py` | shipped |
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
| GitHub search recall (v1.1) | Gated by the code-gap spike (SPE-297 removed the script; seed in `tests/evals/fixtures`) before build; search arXiv IDs + title variants + author repos; surface the raw results in evidence so misses are visible. |
| S2 rate limits (v1); GitHub rate limits (v1.1, the real bottleneck) | Net-new Redis cache + backoff from day one (reuse the `embeddings_client.py` backoff pattern; add the cache, which does not yet exist in any client). |
| Code-gap staleness (v1.1) | "As of `<date>`" stamp + re-score/decay policy; unweighted chip first. |
| Judgment quality | Typed Jev judgments with calibrated confidence; golden-set gate plus a calibration report; low-confidence marker in the product rather than a hidden number. |
| TypeSafe rate limits / outages | SDK retries; `score_paper_task` retries after `retry_after` and never storms; no nano fallback by design (Stage 2 waits). |

---

## Open Questions

1. Re-score/decay cadence for the time-sensitive code-gap dimension.
2. Stage 1 rules-assisted pre-filter (arXiv metadata heuristics) -- deferred, since cheap
   models make Stage 1 cost negligible; only useful for rate-limit/latency relief.
3. Exact read-time composite formula and how compute-profile buckets (laptop / single GPU
   / cloud) map onto the resource-feasibility sub-score.
4. AGPL implications if the scored index is exposed via a public API later
   (`proposal.md` Open Question 4).
