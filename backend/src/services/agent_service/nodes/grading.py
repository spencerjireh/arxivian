"""Grading node for document relevance evaluation."""

import asyncio
import json
from langchain_core.messages import ToolMessage
from src.schemas.langgraph_state import AgentState, GradingResult
from ..context import AgentContext
from ..prompts import get_grading_prompt


async def grade_documents_node(state: AgentState, context: AgentContext) -> AgentState:
    """
    Grade retrieved chunks for relevance to query.

    Uses parallel LLM calls for speed.
    """
    query = state.get("rewritten_query") or state["original_query"]

    # Extract chunks from tool messages
    chunks = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            content = msg.content
            if isinstance(content, str):
                chunks = json.loads(content)
            else:
                chunks = content
            break

    state["retrieved_chunks"] = chunks

    # Grade all chunks in parallel
    async def grade_single_chunk(chunk: dict) -> GradingResult:
        prompt = get_grading_prompt(query or "", chunk)

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
    state["metadata"]["reasoning_steps"].append(
        f"Graded documents ({relevant_count}/{total_count} relevant)"
    )

    # Routing decision
    if relevant_count >= context.top_k:
        state["routing_decision"] = "generate_answer"
    elif state["retrieval_attempts"] >= context.max_retrieval_attempts:
        state["routing_decision"] = "generate_answer"  # Use what we have
        state["metadata"]["reasoning_steps"].append(
            "Max attempts reached, proceeding with available documents"
        )
    else:
        state["routing_decision"] = "rewrite_query"

    return state
