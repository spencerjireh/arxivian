"""Conditional edge functions for graph routing."""

from src.schemas.langgraph_state import AgentState


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


def continue_after_grading(state: AgentState) -> str:
    """Route based on grading results (legacy)."""
    decision = state.get("routing_decision")
    return decision if decision else "generate"


def route_after_router(state: AgentState) -> str:
    """
    Route based on router decision.

    Returns:
        - "execute": Router decided to call a tool
        - "grade": Router decided to generate, but we have retrieved chunks to grade
        - "generate": Router decided to generate response
    """
    decision = state.get("router_decision")

    if not decision:
        # No decision, default to generate
        return "generate"

    if decision.action == "execute_tool":
        return "execute"

    # Action is "generate" - check if we need to grade first
    retrieved_chunks = state.get("retrieved_chunks", [])
    relevant_chunks = state.get("relevant_chunks", [])

    # If we have retrieved chunks but no relevant chunks yet, grade first
    if retrieved_chunks and not relevant_chunks:
        return "grade"

    return "generate"


def route_after_executor(state: AgentState) -> str:
    """
    Route after tool execution.

    Returns:
        - "grade": If retrieve_chunks was called, grade the results
        - "router": Otherwise, go back to router for next decision
    """
    tool_history = state.get("tool_history", [])

    if not tool_history:
        return "router"

    # Get the last executed tool
    last_execution = tool_history[-1]

    # If we just retrieved chunks, grade them
    if last_execution.tool_name == "retrieve_chunks" and last_execution.success:
        return "grade"

    # For other tools, go back to router
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
