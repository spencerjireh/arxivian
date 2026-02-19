"""Conditional edge functions for graph routing."""

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.tools import RETRIEVE_CHUNKS


def continue_after_guardrail(state: AgentState) -> str:
    """Route based on guardrail score."""
    guardrail_result = state.get("guardrail_result")
    if not guardrail_result:
        return "out_of_scope"

    score = guardrail_result.score
    threshold = state["metadata"].get("guardrail_threshold", 75)

    if score >= threshold:
        return "continue"
    else:
        return "out_of_scope"


def route_after_router(state: AgentState) -> str:
    """
    Route based on router decision.

    Returns:
        - "execute": Router decided to call tool(s)
        - "grade": Router decided to generate, but we have retrieved chunks to grade
        - "generate": Router decided to generate response
    """
    decision = state.get("router_decision")

    if not decision:
        return "generate"

    if decision.tool_calls:
        return "execute"

    # Action is "generate" - check if we need to grade first
    retrieved_chunks = state.get("retrieved_chunks", [])
    relevant_chunks = state.get("relevant_chunks", [])

    if retrieved_chunks and not relevant_chunks:
        return "grade"

    return "generate"


def route_after_executor(state: AgentState) -> str:
    """
    Route after tool execution.

    Returns:
        - "confirm": If a tool triggered HITL pause (propose_ingest)
        - "grade": If retrieve_chunks was called in current batch, grade the results
        - "router": Otherwise, go back to router for next decision
    """
    # HITL: if a tool set pause_reason, route to confirm_ingest
    if state.get("pause_reason"):
        return "confirm"

    last_executed = state.get("last_executed_tools", [])

    if not last_executed:
        return "router"

    # Check if retrieve_chunks was in current batch and succeeded
    if RETRIEVE_CHUNKS in last_executed:
        # Verify it succeeded by checking the most recent execution
        for t in reversed(state.get("tool_history", [])):
            if t.tool_name == RETRIEVE_CHUNKS:
                return "grade" if t.success else "router"

    return "router"


def route_after_grading_new(state: AgentState) -> str:
    """
    Route after grading (new architecture).

    Returns:
        - "router": If we need more context (not enough relevant chunks)
        - "generate": If we have enough relevant chunks
    """
    relevant_chunks = state.get("relevant_chunks", [])
    top_k = state.get("metadata", {}).get("top_k", 3)
    max_iterations = state.get("max_iterations", 5)
    iteration = state.get("iteration", 0)

    # If we have enough relevant chunks, generate
    if len(relevant_chunks) >= top_k:
        return "generate"

    # If we've hit max iterations, generate with what we have
    if iteration >= max_iterations:
        return "generate"

    # Otherwise, go back to router for possible query rewrite
    return "router"
