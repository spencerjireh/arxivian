"""Grading node for document relevance evaluation."""

import asyncio
from src.schemas.langgraph_state import AgentState, GradingResult
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_grading_prompt

log = get_logger(__name__)


async def grade_documents_node(state: AgentState, context: AgentContext) -> AgentState:
    """
    Grade retrieved chunks for relevance to query.

    Uses parallel LLM calls for speed.
    """
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

    state["grading_results"] = grading_results
    state["relevant_chunks"] = relevant_chunks

    relevant_count = len(relevant_chunks)
    total_count = len(chunks)

    log.info("grading complete", relevant=relevant_count, total=total_count)

    state["metadata"]["reasoning_steps"].append(
        f"Graded documents ({relevant_count}/{total_count} relevant)"
    )

    # Routing decision
    if relevant_count >= context.top_k:
        state["routing_decision"] = "generate_answer"
        log.debug("routing to generate_answer", reason="enough_relevant_chunks")
    elif state["retrieval_attempts"] >= context.max_retrieval_attempts:
        state["routing_decision"] = "generate_answer"
        state["metadata"]["reasoning_steps"].append(
            "Max attempts reached, proceeding with available documents"
        )
        log.debug("routing to generate_answer", reason="max_attempts_reached")
    else:
        state["routing_decision"] = "rewrite_query"
        log.debug("routing to rewrite_query", reason="insufficient_relevant_chunks")

    return state
