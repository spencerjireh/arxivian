"""Batch evaluation node: replaces per-chunk grading with a single LLM call."""

from langchain_core.runnables import RunnableConfig

from src.schemas.langgraph_state import AgentState, BatchEvaluation
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_batch_evaluation_prompt

log = get_logger(__name__)


def _chunk_fingerprints(chunks: list[dict]) -> list[str]:
    """Sorted fingerprints for stagnation detection across iterations."""
    return sorted(
        f"{c.get('arxiv_id', 'unknown')}:{(c.get('chunk_text') or '')[:100]}"
        for c in chunks
    )


async def evaluate_batch_node(state: AgentState, config: RunnableConfig) -> dict:
    """Evaluate whether retrieved chunks collectively answer the query.

    One LLM call replaces N per-chunk grading calls. When sufficient, promotes
    all retrieved chunks to relevant_chunks. When insufficient and iterations
    remain, suggests a rewritten query for retry.
    """
    context: AgentContext = config["configurable"]["context"]

    query = state.get("rewritten_query") or state.get("original_query") or ""
    chunks = state.get("retrieved_chunks", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", context.max_iterations)

    log.debug("evaluate_batch started", query=query[:100] if query else "", chunks=len(chunks))

    metadata = dict(state.get("metadata", {}))
    reasoning_steps = list(metadata.get("reasoning_steps", []))

    # Stagnation detection: if chunks are identical to the previous iteration,
    # short-circuit with sufficient=True to break the rewrite loop
    current_fingerprints = _chunk_fingerprints(chunks) if chunks else []
    previous_fingerprints = metadata.get("previous_chunk_fingerprints", [])

    if chunks and current_fingerprints == previous_fingerprints:
        log.info(
            "evaluate_batch: stagnation detected", chunks=len(chunks), iteration=iteration
        )
        reasoning_steps.append(
            f"Evaluated retrieval ({len(chunks)} chunks): stagnation detected, promoting all"
        )
        return {
            "evaluation_result": BatchEvaluation(
                sufficient=True,
                reasoning="Retrieval returned identical chunks as previous iteration. "
                "Promoting all as best-effort.",
            ),
            "relevant_chunks": chunks,
            "metadata": {
                **metadata,
                "previous_chunk_fingerprints": current_fingerprints,
                "reasoning_steps": reasoning_steps,
            },
        }

    # Empty chunks -> insufficient, no LLM call needed
    if not chunks:
        log.info("evaluate_batch: no chunks to evaluate")
        evaluation = BatchEvaluation(sufficient=False, reasoning="No chunks retrieved")
        reasoning_steps.append("Evaluated retrieval: no chunks retrieved")
        return {
            "evaluation_result": evaluation,
            "relevant_chunks": [],
            "metadata": {**metadata, "reasoning_steps": reasoning_steps},
        }

    # Single LLM call for batch evaluation
    system, user = get_batch_evaluation_prompt(query, chunks)

    evaluation = await context.llm_client.generate_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=BatchEvaluation,
    )

    log.info(
        "evaluate_batch result",
        sufficient=evaluation.sufficient,
        total_chunks=len(chunks),
        has_rewrite=evaluation.suggested_rewrite is not None,
        reasoning=evaluation.reasoning[:100],
    )

    updates: dict = {
        "evaluation_result": evaluation,
        "metadata": {**metadata},
    }

    if evaluation.sufficient:
        # Promote all retrieved chunks -- they're already ranked by hybrid search
        updates["relevant_chunks"] = chunks
        reasoning_steps.append(
            f"Evaluated retrieval ({len(chunks)} chunks): sufficient"
        )
    elif iteration >= max_iterations:
        # Max iterations reached -- promote all anyway (best-effort)
        updates["relevant_chunks"] = chunks
        reasoning_steps.append(
            f"Evaluated retrieval ({len(chunks)} chunks): insufficient but max iterations reached, "
            f"promoting all"
        )
        log.info("evaluate_batch: max iterations, promoting all chunks", iteration=iteration)
    elif evaluation.suggested_rewrite:
        # Insufficient with rewrite suggestion -- trigger retry loop
        updates["rewritten_query"] = evaluation.suggested_rewrite
        updates["relevant_chunks"] = []
        reasoning_steps.append(
            f"Evaluated retrieval ({len(chunks)} chunks): insufficient, "
            f"rewriting to '{evaluation.suggested_rewrite[:80]}'"
        )
        log.info(
            "evaluate_batch: rewrite suggested",
            original=query[:80] if query else "",
            rewritten=evaluation.suggested_rewrite[:80],
        )
    else:
        # Insufficient, no rewrite suggestion -- promote all (best-effort)
        updates["relevant_chunks"] = chunks
        reasoning_steps.append(
            f"Evaluated retrieval ({len(chunks)} chunks): insufficient, no rewrite suggested, "
            f"promoting all"
        )

    updates["metadata"]["reasoning_steps"] = reasoning_steps
    updates["metadata"]["previous_chunk_fingerprints"] = current_fingerprints
    return updates
