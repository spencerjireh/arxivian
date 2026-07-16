# Tiered Generation Strategy

> **Status: Archived (pre-pivot).** Superseded by
> `docs/design/agent-graph-refactor.md` -- this doc describes the pre-refactor 7-node
> graph (`guardrail -> router -> grade -> generate`) that no longer exists. Retained for
> historical context only; not updated for the feed pivot (see
> `docs/product/feed-prd.md`).

Design doc for refining the agent's retrieval-to-generation flow with confidence-based response tiers.

## Problem

The current agent has a binary response model: it either finds enough relevant chunks and answers strictly from them, or exhausts retry loops and answers with whatever scraps it found -- still constrained to "ONLY the provided context." There is no graceful degradation when the knowledge base lacks coverage on a topic.

This leads to poor UX in two scenarios:
1. **Partial coverage**: The KB has some relevant papers but not enough to fully answer. The agent either gives a thin answer or wastes cycles retrying.
2. **No coverage**: The KB has nothing relevant. The agent loops through max_iterations of query rewrites searching empty space, then produces an unhelpful "I don't have enough information" response.

## Solution: Three-Tier Response Model

Introduce a confidence-tiered generation strategy based on retrieval results.

### Tiers

| Tier | Condition | Generation Behavior |
|------|-----------|---------------------|
| **Full RAG** | `relevant_count >= top_k` | Answer strictly from chunks. Cite as `[arxiv_id]`. Current behavior, unchanged. |
| **Hybrid** | `0 < relevant_count < top_k` | Use chunks as primary evidence (cited). Supplement gaps with general knowledge, clearly delineated inline (e.g., "According to [2401.12345]... More broadly in this field..."). |
| **Fallback** | `relevant_count == 0` | Answer using general knowledge. Proactively suggest searching arXiv with specific terms extracted from the query. Never fabricate citations. |

### Retry Strategy: One Retry, Then Tier

Replace the current exhaustive retry loop (up to `max_iterations = 5`) with:

1. First retrieval + grading
2. If below threshold: one query rewrite + re-retrieve + re-grade
3. After second attempt: determine tier based on final `relevant_count` and generate

Rationale: the first query rewrite catches ~80% of terminology mismatches. Further retries search the same empty space. Tiered generation provides a better exit than more retries.

The `max_iterations` parameter remains on `AgentContext` but its effective value for the retrieve-grade loop becomes 2. The router's overall iteration cap still applies to the full graph traversal (tool chaining, multi-step workflows).

### Router Bypass (Preserved)

The router can still decide to generate directly without retrieval for:
- Follow-up questions where context is already sufficient
- Queries where tool results (non-retrieval) already provide the answer

Tiered logic only applies to the post-retrieval path.

## Detailed Behavior

### Full RAG Tier

No changes from current behavior.

**System prompt**: "Answer based ONLY on the provided context and tool results. Cite sources as [arxiv_id]."

### Hybrid Tier

Chunks are the primary evidence. General knowledge fills gaps but is clearly marked.

**System prompt addition**:
```
Answer using the provided context as your primary evidence, cited as [arxiv_id].
Where the retrieved context is insufficient to fully address the question, you may
supplement with your general knowledge of the field. When doing so, use natural
transitions that make the source clear (e.g., "According to [2401.12345]..."
for paper-sourced claims, and "More broadly in the literature..." or "Generally
in this area..." for general knowledge).

CRITICAL: Never fabricate paper titles, arXiv IDs, or citations. Only cite
papers that appear in the provided context.
```

**Inline marker examples** (guidance for the LLM, not enforced structurally):
- "According to [2401.12345], transformer attention scales quadratically..."
- "More broadly, recent work in efficient attention has explored linear approximations..."
- "The authors in [2403.67890] propose X, which aligns with the general trend toward..."

### Fallback Tier

General knowledge answer with a concrete arXiv search suggestion.

**System prompt addition**:
```
No relevant papers were found in the knowledge base for this query. Provide a
helpful answer using your general knowledge of the topic. Be honest that this
is not sourced from specific papers in the system.

At the end of your response, suggest searching arXiv. Extract 2-3 specific
search terms from the query and propose them naturally. Example:
"I don't have papers on this topic in your knowledge base yet. Would you like
me to search arXiv? I'd look for papers on [specific terms]."

CRITICAL: Never fabricate paper titles, arXiv IDs, or citations.
```

### ArXiv Follow-Up Handling

When the agent suggests an arXiv search in fallback mode and the user responds affirmatively (e.g., "yes", "sure, search for that", "go ahead"):

1. The router recognizes this as a continuation of the fallback suggestion
2. It extracts the search terms from the previous assistant message (the arXiv suggestion)
3. It calls `arxiv_search` with those terms
4. Results are presented to the user
5. The user picks which papers to ingest (HITL gate -- ingestion is expensive)

This requires the router prompt to be aware of the previous fallback suggestion context. The conversation history already flows into the router, so this is primarily a prompt engineering change -- instruct the router to recognize affirmative follow-ups to arXiv suggestions and extract the proposed terms.

**Future consideration**: Explicit HITL (human-in-the-loop) confirmation step before ingestion, potentially as a graph interrupt or a structured UI element rather than relying on natural language confirmation.

## State Changes

### New Fields on `AgentState`

```python
# In AgentState TypedDict
generation_mode: str           # "full_rag" | "hybrid" | "fallback"
retrieval_confidence: float    # relevant_count / max(retrieved_count, 1)
suggested_search_terms: list[str]  # Terms extracted for arXiv suggestion (fallback tier)
```

### New Field on `AgentContext`

```python
# Configurable threshold for future ratio-based tuning
confidence_threshold: float = 0.5  # Not used initially; available for experimentation
```

## Graph Changes

### Topology

The graph structure remains unchanged:
```
START -> guardrail -> [out_of_scope | router]
router -> [executor | grade | generate]
executor -> [grade | router]
grade -> [router | generate]
generate -> END
```

### Modified Components

| Component | Change |
|-----------|--------|
| `grade_documents_node` | Compute `retrieval_confidence` and `generation_mode`. Set `generation_mode` based on `relevant_count` vs `top_k`. |
| `route_after_grading_new` | After one retry (iteration >= 2 for the retrieve-grade loop), route to `generate` regardless of chunk count. Let `generation_mode` handle the response quality. |
| `generate_answer_node` | Read `generation_mode` from state. Select system prompt variant accordingly. For fallback, extract and include suggested search terms. |
| `prompts.py` | Add `HYBRID_SYSTEM_PROMPT` and `FALLBACK_SYSTEM_PROMPT` constants. Add prompt builder methods for each tier. |
| `ROUTER_SYSTEM_PROMPT` | Add guidance for recognizing arXiv follow-up confirmations. |

### Unchanged Components

| Component | Why |
|-----------|-----|
| `guardrail_node` | Relevance validation is orthogonal to generation tier |
| `executor_node` | Tool execution is tier-agnostic |
| `RetrieveChunksTool` | Retrieval mechanics don't change |
| Graph topology | No new nodes or edges needed |

## Prompt Changes Summary

| Prompt | Change |
|--------|--------|
| `ANSWER_SYSTEM_PROMPT` | Rename to `FULL_RAG_SYSTEM_PROMPT`. No content change. |
| `HYBRID_SYSTEM_PROMPT` | New. Chunks as primary + general knowledge with inline markers. |
| `FALLBACK_SYSTEM_PROMPT` | New. General knowledge + arXiv search suggestion. |
| `ROUTER_SYSTEM_PROMPT` | Add section on recognizing affirmative follow-ups to arXiv suggestions. |
| `get_grading_prompt` | No change (boolean grading preserved). |
| `get_rewrite_prompt` | No change. |

## Configuration

All thresholds are on `AgentContext`, configurable per-request via `RunnableConfig`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `top_k` | 3 | Minimum relevant chunks for full RAG tier |
| `confidence_threshold` | 0.5 | Reserved for future ratio-based tier selection |
| `max_iterations` | 5 | Overall graph iteration cap (unchanged) |
| `max_retrieval_attempts` | 2 | Retrieve-grade loop cap (changed from 3) |

## Migration

This is a behavioral change, not a data migration. No database changes required.

- Existing conversations continue to work (router bypass preserved)
- Default behavior for well-covered queries is identical (full RAG tier)
- New behavior only activates when retrieval falls short

## Testing Strategy

### Unit Tests
- `test_grade_documents_node`: Verify `generation_mode` is set correctly for each tier
- `test_route_after_grading`: Verify routing with new retry cap
- `test_generate_answer_node`: Verify correct prompt variant selected per tier
- `test_prompt_builder`: Verify hybrid and fallback prompts are well-formed

### Integration Tests
- Full graph run with a query that has full coverage -> full RAG
- Full graph run with a query that has partial coverage -> hybrid
- Full graph run with a query that has no coverage -> fallback with arXiv suggestion
- Follow-up "yes, search arXiv" after fallback -> router triggers arxiv_search

### Evals
- Compare answer quality across tiers using Langfuse scoring
- Measure hallucination rate in hybrid vs full RAG mode
- Track false positive rate of arXiv suggestions (does the suggestion make sense?)

## Open Questions

1. **HITL for ingestion**: Current design relies on natural language ("would you like me to ingest these?"). A structured UI confirmation (e.g., checkboxes next to search results) would be more reliable but requires frontend work. Decide scope for v1.
2. **Streaming indicators**: Should the frontend show which tier is being used? E.g., a subtle label like "Answering from papers" vs "Answering from general knowledge." Requires a new SSE event type.
3. **Langfuse tracking**: Should `generation_mode` be logged as a Langfuse score/metadata for observability? Likely yes -- enables filtering traces by tier.
