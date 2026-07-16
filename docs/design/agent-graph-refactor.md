# Agent Graph Refactor: 14 LLM Calls -> 3

## Context

The current agent graph makes ~14 LLM calls for a simple RAG query ("what does paper X say about Y?"), assuming ~10 retrieved chunks graded individually: guardrail(1) + router(1) + grade(10) + generate(1) + rewrite(1) = 14. The grading node alone makes 10 parallel calls (one per retrieved chunk). Community-converged production patterns (Adaptive RAG, CRAG, Adaline Labs research) show that batch-level evaluation + intent-based routing achieves equivalent or better quality at 3-4 calls. This refactor reduces complexity (7 nodes -> 6), cost (~75% fewer LLM calls), and latency while preserving the HITL flow, tool registry, and SSE streaming contract.

**LLM calls per query after refactor:**
| Query Type | Calls | Path |
|---|---|---|
| Simple RAG | 3 | classify(1) -> retrieve(0) -> evaluate(1) -> generate(1) |
| Follow-up ("explain more") | 1 | fast-path(0) -> generate(1) |
| Tool-only (list papers) | 2 | classify(1) -> execute(0) -> classify(1, generate) |
| Out-of-scope | 2 | classify(1) -> out_of_scope(1) |
| RAG with rewrite | 5 | classify(1) -> retrieve(0) -> evaluate(1, fail) -> classify(1) -> retrieve(0) -> evaluate(1) -> generate(1) |

---

## Graph Topology Change

### Before (7 nodes)
```
START -> guardrail -> [out_of_scope | router]
router -> [executor | grade_documents | generate]
executor -> [confirm_ingest | grade_documents | router]
grade_documents -> [router | generate]
generate -> END
out_of_scope -> END
```

### After (6 nodes)
```
START -> classify_and_route -> [out_of_scope | generate | executor]
executor -> [confirm_ingest | evaluate_batch | classify_and_route]
confirm_ingest -> classify_and_route  (iteration > 0, scope_score carried forward, not re-evaluated)
evaluate_batch -> [generate | classify_and_route]
generate -> END
out_of_scope -> END
```

---

## Change 1: Merge guardrail + router -> classify_and_route

Two separate LLM calls (scope scoring + tool selection) become one.

### New schema (`langgraph_state.py`)

```python
class ClassificationResult(BaseModel):
    intent: Literal["out_of_scope", "direct", "execute"] = Field(...)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    scope_score: int = Field(..., ge=0, le=100)
    reasoning: str = Field(...)
```

Note: no `model_config = ConfigDict(extra="forbid")` -- matches the convention of existing schemas (`GuardrailScoring`, `RouterDecision`, `GradingResult`) which all omit it.

- `"out_of_scope"` -- replaces `GuardrailScoring.is_in_scope == False`
- `"direct"` -- query answerable from conversation context, skip retrieval
- `"execute"` -- call tools (includes RAG: `tool_calls=[retrieve_chunks(...)]`)

### Fast-path preserved

The existing regex-based conversational follow-up detection (`SHORT_FOLLOWUP` pattern in guardrail.py:15-17) stays. Short follow-ups like "yes", "tell me more", "explain" with in-scope conversation history skip the LLM entirely and return `ClassificationResult(intent="direct", scope_score=100)`.

### Guard against LLM returning `"direct"` incorrectly

The LLM can see `intent="direct"` in the schema and may return it for queries that actually need retrieval. The `classify_and_route` prompt must instruct: "Only return intent=direct when the conversation already contains retrieved sources that address the current question." Additionally, `route_after_classify` enforces a structural safety net: if `intent=="direct"` but `retrieved_chunks` exist in state and `relevant_chunks` is empty, downgrade to `"execute"` with `tool_calls=[retrieve_chunks(...)]`. This carries forward the existing safety logic from `route_after_router` (edges.py:39-46).

### Rewrite-loop and post-confirmation behavior

When `evaluate_batch` routes back for a rewrite, `classify_and_route` is called again with `iteration > 0`. On rewrite iterations, the prompt skips scope assessment (score carried forward) and only does tool selection, with `rewritten_query` as the query.

The same `iteration > 0` skip applies after `confirm_ingest -> classify_and_route`: the HITL flow already validated scope in the initial classification, so re-evaluating after user confirms/declines would risk misclassifying the changed conversation state as out-of-scope. The original `scope_score` carries forward.

**Mechanism:** `confirm_ingest` must increment `iteration` in its return dict (currently it does not touch this field). This ensures `classify_and_route` sees `iteration > 0` on entry and skips scope assessment. Without this, the node would re-evaluate scope after user confirmation. The `evaluate_batch` rewrite path already increments `iteration` naturally, but `confirm_ingest` needs an explicit `{"iteration": state.get("iteration", 0) + 1}` added to its return dict.

### Max-iterations fallback

When `iteration > max_iterations`, force `ClassificationResult(intent="direct")` without an LLM call (same as current router forced-generate behavior).

---

## Change 2: Replace per-chunk grading -> evaluate_batch

N parallel LLM calls (one per chunk) become one batch evaluation call.

### New schema (`langgraph_state.py`)

```python
class BatchEvaluation(BaseModel):
    sufficient: bool = Field(...)
    reasoning: str = Field(...)
    suggested_rewrite: str | None = Field(default=None)
```

### Behavior

- Reads `retrieved_chunks` from state
- One LLM call evaluates the entire set against the query
- If `sufficient=True`: promotes all `retrieved_chunks` to `relevant_chunks` (already ranked by hybrid search score)
- If `sufficient=False` and `suggested_rewrite` present and iterations remain: writes `{"rewritten_query": suggested_rewrite}` in its return dict, routes back to `classify_and_route` (which reads `rewritten_query` from state on the next iteration). Note: `rewritten_query` already exists in `AgentState` (line 106) -- no schema change needed.
- If `sufficient=False` but max iterations reached: promotes all chunks anyway (best-effort), routes to `generate`
- Combines evaluation + rewrite suggestion in one call (replaces both `get_grading_prompt` and `get_rewrite_prompt`)

### Why batch works here

Your hybrid search (pgvector + full-text + RRF) already ranks chunks by relevance. Per-chunk LLM grading was re-checking what the search ranking already decided. Batch evaluation asks the more useful question: "is this set of results collectively sufficient to answer the query?" -- which catches the case where results are topically relevant but miss the specific angle the user asked about.

---

## Change 3: State schema updates

### AgentState field changes

| Field | Action | Notes |
|---|---|---|
| `guardrail_result` | **Remove** | Replaced by `classification_result` |
| `router_decision` | **Remove** | Replaced by `classification_result` |
| `grading_results` | **Remove** | Replaced by `evaluation_result` |
| `classification_result` | **Add** | `ClassificationResult \| None` |
| `evaluation_result` | **Add** | `BatchEvaluation \| None` |
| `retrieval_attempts` | **Keep** | Still incremented by `executor.py` when `extends_chunks=True`. Used in `service.py` METADATA event, `_build_turn_data`, and Langfuse score submission. |
| `last_executed_tools` | **Keep** | Still set by `executor.py`, read by `route_after_executor` to decide `evaluate_batch` vs `classify_and_route` routing. |
| Everything else | **Keep** | `retrieved_chunks`, `relevant_chunks`, `tool_outputs`, `tool_history`, HITL fields, metadata, messages all unchanged |

### Schemas removed from `langgraph_state.py`

- `GuardrailScoring` -- subsumed by `ClassificationResult`
- `RouterDecision` -- subsumed by `ClassificationResult`
- `GradingResult` -- subsumed by `BatchEvaluation`

### Schemas kept unchanged

- `ToolCall`, `ToolExecution`, `InjectionScan`, `AgentMetadata`, `ToolOutput`

---

## Change 4: New edge functions

### `edges.py` -- full rewrite (3 functions replacing 4)

```python
def route_after_classify(state) -> str:
    # "out_of_scope" if intent=="out_of_scope" or scope_score < threshold
    # "execute" if intent=="execute" with tool_calls
    # Safety net (carries forward edges.py:39-46): if intent=="direct" but
    #   retrieved_chunks exist and relevant_chunks is empty, route to "evaluate"
    #   instead of "generate" -- prevents skipping ungraded chunks
    # "generate" if intent=="direct" or no tool_calls (and no ungraded chunks)

def route_after_executor(state) -> str:
    # "confirm" if pause_reason set (HITL)
    # "evaluate" if RETRIEVE_CHUNKS in last_executed_tools and succeeded
    # "classify" otherwise (loop back for next decision)

def route_after_eval(state) -> str:
    # "generate" if sufficient==True or max iterations reached
    # "classify" if insufficient and iterations remain (rewrite loop)
```

**Deleted:** `continue_after_guardrail`, `route_after_router`, `route_after_grading_new`

---

## Change 5: Prompt templates

### `prompts.py` changes

| Function | Action |
|---|---|
| `get_context_aware_guardrail_prompt` | **Delete** |
| `get_router_prompt` | **Delete** |
| `get_grading_prompt` | **Delete** |
| `get_rewrite_prompt` | **Delete** |
| `GUARDRAIL_SYSTEM_PROMPT` | **Delete** |
| `ROUTER_SYSTEM_PROMPT` | **Delete** |
| `get_classify_and_route_prompt` | **Add** -- merged scope + routing prompt |
| `get_batch_evaluation_prompt` | **Add** -- holistic chunk set evaluation |
| `CLASSIFY_AND_ROUTE_SYSTEM_PROMPT` | **Add** -- combined system prompt |
| `ANSWER_SYSTEM_PROMPT` | **Keep** unchanged |
| `PromptBuilder` | **Keep** unchanged |

The new `CLASSIFY_AND_ROUTE_SYSTEM_PROMPT` combines guardrail scoring rules with the existing `ROUTER_SYSTEM_PROMPT` routing priority rules (lines 68-132 of current prompts.py). The routing priority rules (CONTENT QUESTIONS -> retrieve_chunks, KB BROWSING -> list_papers, etc.) transfer directly.

---

## Change 6: Service layer updates

### `service.py` -- targeted edits (not a rewrite)

**NODE_TO_STEP and NODE_MESSAGES maps** (lines 61-78):
```python
NODE_TO_STEP = {
    "classify_and_route": "classifying",
    "out_of_scope": "out_of_scope",
    "executor": "executing",
    "evaluate_batch": "evaluating",
    "generate": "generation",
    "confirm_ingest": "confirming",
}
NODE_MESSAGES = {
    "classify_and_route": "Classifying query...",
    "out_of_scope": "Generating out-of-scope response...",
    "evaluate_batch": "Evaluating retrieval quality...",
    "generate": "Generating answer...",
    "confirm_ingest": "Waiting for confirmation...",
}
```

**`_consume_stream` node handlers** (lines 280-382):
- Replace `node_name == "guardrail"` block -> `node_name == "classify_and_route"` (read `classification_result.scope_score` and `.intent`)
- Delete `node_name == "router"` block (no separate router node)
- Replace `node_name == "grade_documents"` block -> `node_name == "evaluate_batch"`:
  - Status details: `{"sufficient": batch_eval.sufficient, "total": len(state["retrieved_chunks"]), "reasoning": batch_eval.reasoning}` (note: `total` comes from `retrieved_chunks` count, not `grading_results` which no longer exists)
  - Emit SOURCES when `sufficient=True` OR when max iterations reached (best-effort promotion), reading from `relevant_chunks` (which `evaluate_batch` populates by promoting `retrieved_chunks`)
- Keep all other blocks unchanged

**`initial_state` dict** (in `ask_stream`):
- `guardrail_result: None` -> `classification_result: None`
- `router_decision: None` -> remove
- `grading_results: []` -> `evaluation_result: None`

**`guardrail_result` references in `service.py` (4 sites, all -> `classification_result.scope_score`):**
1. `_consume_stream` guardrail handler (line ~280) -- replace node check and field reads
2. `ask_stream` final metadata block (line ~630-631) -- `guardrail_result.score` -> `classification_result.scope_score`
3. `_build_turn_data` (line ~932-943) -- `guardrail_result.score` -> `classification_result.scope_score`
4. Langfuse score submission (line ~651-656) -- `guardrail_score` derived from `classification_result.scope_score`

---

## Change 7: Minor node updates

### `executor.py` -- 1 line change
```python
# Line ~57: router_decision -> classification_result
classification = state.get("classification_result")
if not classification or not classification.tool_calls:
```

### `generation.py` -- 2 changes

The current `retrieval_attempts >= max_retrieval_attempts` fallback (lines 42-47) that appends a "limited sources" note is **replaced** by checking `evaluation_result.sufficient`. The `evaluate_batch` node now owns the "max iterations reached, promote all chunks anyway" logic, so by the time `generate` runs, `relevant_chunks` is always populated and `evaluation_result` tells us whether the set was sufficient or best-effort:

```python
# Replace lines 42-47: retrieval_attempts fallback -> evaluation_result check
batch_eval = state.get("evaluation_result")
if batch_eval and not batch_eval.sufficient:
    builder.with_note(
        "Limited sources were found in the knowledge base. "
        "Some chunks are available but they do not fully cover the question."
    )
```

The `retrieval_attempts` read at line 22 and its use in logging (line 28) can stay -- it's still useful for observability. Only the conditional at line 43 changes.

### `out_of_scope.py` -- ~3 line changes
```python
# guardrail_result -> classification_result
# .score -> .scope_score
# .reasoning stays .reasoning
```

### `confirm_ingest.py` -- 1 addition
```python
# Add iteration increment to return dict so classify_and_route skips scope on re-entry
return {
    ...,
    "iteration": state.get("iteration", 0) + 1,
}
```

---

## Files Summary

### New files (2)
- `backend/src/services/agent_service/nodes/classify_and_route.py`
- `backend/src/services/agent_service/nodes/evaluate_batch.py`

### Deleted files (3)
- `backend/src/services/agent_service/nodes/guardrail.py`
- `backend/src/services/agent_service/nodes/router.py`
- `backend/src/services/agent_service/nodes/grading.py`

### Modified files (10)
- `backend/src/schemas/langgraph_state.py` -- add 2 schemas, remove 3, update AgentState
- `backend/src/services/agent_service/graph_builder.py` -- new topology
- `backend/src/services/agent_service/edges.py` -- 3 new functions replacing 4
- `backend/src/services/agent_service/prompts.py` -- add 2 prompts, delete 4
- `backend/src/services/agent_service/nodes/__init__.py` -- update exports
- `backend/src/services/agent_service/nodes/executor.py` -- 1 field rename
- `backend/src/services/agent_service/nodes/generation.py` -- 1 condition change
- `backend/src/services/agent_service/nodes/out_of_scope.py` -- field renames
- `backend/src/services/agent_service/nodes/confirm_ingest.py` -- add iteration increment to return dict
- `backend/src/services/agent_service/service.py` -- node maps + _consume_stream handlers

### Unchanged
- All tool files (`tools/*.py`), `context.py`, `security.py`
- `BaseTool`, `ToolRegistry`, `ToolResult`
- All SSE event types and schemas (`schemas/stream.py`)
- `StreamRequest` schema, API endpoint (`routers/stream.py`)
- HITL two-stream flow (ask_stream/resume_stream checkpoint/resume logic)

---

## Test Updates

| Test File | Change |
|---|---|
| `test_edges.py` | **Rewrite** -- new edge functions, new test classes |
| `test_guardrail.py` | **Rewrite** -> `test_classify_and_route.py` (injection scanner + conversation formatter tests stay, node tests update assertions) |
| `test_executor.py` | **Minor** -- `router_decision` -> `classification_result` in fixtures (also imports `RouterDecision` -> `ClassificationResult`) |
| `test_out_of_scope_eval.py` | **Minor** -- imports `GuardrailScoring` and sets `state["guardrail_result"]` -> change to `ClassificationResult` and `state["classification_result"]` |
| `test_confirm_ingest_node.py` | **Minor** -- verify return dict includes incremented `iteration` |
| `test_service_hitl.py` | **Moderate** -- node name changes in mock events |
| `test_tools.py`, `test_list_papers.py`, `test_propose_ingest.py`, `test_ingest_tool_quota.py` | **None** (verified: no transitive imports of `GuardrailScoring`, `RouterDecision`, or `GradingResult`) |
| `test_stream_router.py` (API) | **None** (SSE event types unchanged) |
| Eval tests | See below |

### New test file
- `test_evaluate_batch.py` -- batch evaluation node: empty chunks, sufficient, insufficient, rewrite suggestion, max iterations

### Eval test redesign

The evals need more than node name updates because the capabilities being tested have changed shape:

| Eval File | Change |
|---|---|
| `test_guardrail_eval.py` + `test_router_eval.py` | **Merge** into `test_classify_and_route_eval.py`. Both now test aspects of the same `classify_and_route` node. Scenarios from both files carry over: scope scoring scenarios from guardrail eval, tool selection scenarios from router eval. |
| `test_grading_eval.py` | **Redesign**. Per-chunk relevance grading no longer exists. Replace with batch sufficiency evaluation scenarios: "is this chunk set collectively sufficient to answer the query?" This is a different capability -- the eval rubric, scenarios, and pass criteria all need rethinking. |
| `test_answer_quality_eval.py` | **Minor** -- verify quality holds with batch-promoted chunks (all retrieved chunks promoted instead of only graded-relevant ones). |
| `test_multi_turn_eval.py` | **Minor** -- node name updates in event assertions. |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Combined classify prompt is too complex | Lower routing accuracy | Eval suite (`test_router_eval.py`, `test_guardrail_eval.py`) catches regressions. The prompt follows same step-by-step structure as current router prompt. |
| Batch evaluation less precise than per-chunk | Some irrelevant chunks reach generation | Chunks already ranked by hybrid search score. Generation prompt's SOURCING TIERS handle mixed quality. Eval suite (`test_grading_eval.py`, `test_answer_quality_eval.py`) catches quality drops. **Pre-merge gate:** run `test_answer_quality_eval.py` against both old (per-chunk filtered) and new (batch-promoted) pipelines on the same scenario set before deleting the old grading node. If answer quality degrades beyond the eval's pass threshold, add a `top_n` cap to `evaluate_batch` that only promotes the highest-ranked subset rather than all chunks. |
| In-flight HITL checkpoints break on deploy | Users with pending confirmations get errors | Existing `CHECKPOINT_EXPIRED` handling in `resume_stream` covers this gracefully. Redis TTL expires stale checkpoints. Deploy during low traffic. |
| "direct" intent misclassifies a query that needs retrieval | Thin answers without sources | Three layers: (1) prompt instruction tells LLM to only return `direct` when conversation already contains retrieved sources for the topic, (2) `route_after_classify` structural guard downgrades `direct` to `execute` when ungraded `retrieved_chunks` exist in state, (3) generation prompt's NO SOURCES tier prompts user to ask for search as a last resort. |
| Rewrite loop re-evaluates scope unnecessarily | Wasted tokens in rewrite prompt | `is_rewrite=True` flag skips scope assessment, only routes tools. Score carried from first classification. |

---

## Rollback Strategy

This refactor touches 10+ files and deletes 3 node files. Rollback considerations:

- **Single-commit boundary.** All changes (steps 1-11) land in one commit. If anything breaks post-merge, `git revert <sha>` restores the entire old graph in one operation.
- **In-flight HITL checkpoints.** Existing `CHECKPOINT_EXPIRED` handling in `resume_stream` covers stale checkpoints gracefully. Redis TTL (default 1h) expires them. Deploy during low-traffic window to minimize affected sessions.
- **No database migrations.** The refactor is purely application-layer (LangGraph state, prompts, nodes). No Alembic migrations means no rollback coordination with the DB.
- **Eval gate before merge.** Run `just eval` on the complete refactor branch. If any eval regresses beyond its pass threshold, do not merge. This is the primary safety net -- the refactor should not land without passing evals.

---

## Implementation Order

1. Add `ClassificationResult` and `BatchEvaluation` schemas to `langgraph_state.py` (alongside old ones)
2. Add `get_classify_and_route_prompt` and `get_batch_evaluation_prompt` to `prompts.py`
3. Create `classify_and_route.py` and `evaluate_batch.py` nodes
4. Rewrite `edges.py` with new edge functions
5. Rewrite `graph_builder.py` with new topology
6. Update `nodes/__init__.py` exports
7. Update `executor.py`, `generation.py`, `out_of_scope.py`, `confirm_ingest.py` (minor field renames + iteration increment)
8. Update `service.py` (node maps, `_consume_stream`, `initial_state`, turn data helpers)
9. Remove old schemas (`GuardrailScoring`, `RouterDecision`, `GradingResult`) and old fields from `AgentState`
10. Delete old node files (`guardrail.py`, `router.py`, `grading.py`)
11. Remove old prompt functions
12. Update/rewrite tests
13. Run `just lint && just check && just test`

---

## Verification

1. **Lint + types**: `just lint && just check` (zero errors)
2. **Unit tests**: `just test tests/unit/` (all pass, updated tests cover new nodes/edges)
3. **API tests**: `just test tests/api/` (SSE event contract unchanged)
4. **Eval suite**: `just eval` (routing accuracy, grading quality, answer quality, guardrail classification -- all at or above current baselines)
5. **Manual smoke test**: docker-compose up, send a RAG query via frontend, verify 3 LLM calls in Langfuse trace (classify -> evaluate -> generate)
6. **HITL test**: trigger paper ingestion flow end-to-end (ask_stream -> CONFIRM_INGEST -> resume_stream), verify checkpoint resume works with new graph topology
