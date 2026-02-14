"""Grading node for document relevance evaluation."""

import asyncio

from langchain_core.runnables import RunnableConfig

from src.schemas.langgraph_state import AgentState, GradingResult
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_grading_prompt, get_rewrite_prompt

log = get_logger(__name__)


async def grade_documents_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Grade retrieved chunks for relevance to query.

    Uses parallel LLM calls for speed. When too few relevant chunks are
    found and iterations remain, rewrites the query inline (replaces
    the separate rewrite node).
    """
    context: AgentContext = config["configurable"]["context"]

    query = state.get("rewritten_query") or state["original_query"]

    # Get chunks from state (set by executor_node)
    chunks = state.get("retrieved_chunks", [])
    log.debug("grading started", query=query[:100] if query else "", chunks=len(chunks))

    # Grade all chunks in parallel
    async def grade_single_chunk(chunk: dict) -> GradingResult:
        prompt = get_grading_prompt(query or "", chunk)

        log.debug("grading chunk", chunk_id=chunk["chunk_id"], arxiv_id=chunk["arxiv_id"])

        result = await context.llm_client.generate_structured(
            messages=[{"role": "user", "content": prompt}],
            response_format=GradingResult,
        )
        result.chunk_id = chunk["chunk_id"]
        return result

    grading_tasks = [grade_single_chunk(chunk) for chunk in chunks]
    grading_results = await asyncio.gather(*grading_tasks)

    # Filter relevant chunks
    relevant_chunks = [chunk for chunk, grade in zip(chunks, grading_results) if grade.is_relevant]

    relevant_count = len(relevant_chunks)
    total_count = len(chunks)

    log.info("grading complete", relevant=relevant_count, total=total_count)

    metadata = dict(state.get("metadata", {}))
    reasoning_steps = list(metadata.get("reasoning_steps", []))
    reasoning_steps.append(f"Graded documents ({relevant_count}/{total_count} relevant)")

    # Inline rewrite: if not enough relevant chunks and iterations remain
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", context.max_iterations)
    rewritten_query = None

    if relevant_count < context.top_k and iteration < max_iterations:
        feedback = "\n".join(
            f"- {chunk['arxiv_id']}: "
            f"{'RELEVANT' if g.is_relevant else 'NOT RELEVANT'} - {g.reasoning}"
            for chunk, g in zip(chunks[:3], grading_results[:3])
        )
        rewritten_query = (
            await context.llm_client.generate_completion(
                messages=[{"role": "user", "content": get_rewrite_prompt(query or "", feedback)}],
                temperature=0.5,
            )
        ).strip()
        reasoning_steps.append(f"Rewrote query: '{rewritten_query}'")
        log.info(
            "query rewritten in grading",
            original=query[:80] if query else "",
            rewritten=rewritten_query[:80],
        )

    return {
        "grading_results": grading_results,
        "relevant_chunks": relevant_chunks,
        "rewritten_query": rewritten_query,
        "metadata": {**metadata, "reasoning_steps": reasoning_steps},
    }
