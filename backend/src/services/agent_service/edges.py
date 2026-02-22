"""Conditional edge functions for graph routing."""

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.tools import RETRIEVE_CHUNKS


def route_after_classify(state: AgentState) -> str:
    """Route based on classification result.

    Returns:
        - "out_of_scope": Query is out of scope
        - "execute": Classification decided to call tool(s)
        - "evaluate": Safety net -- intent is "direct" but ungraded chunks exist
        - "generate": Intent is "direct" and no ungraded chunks
    """
    result = state.get("classification_result")
    if not result:
        return "out_of_scope"

    threshold = state["metadata"].get("guardrail_threshold", 75)

    # Out of scope by intent or score
    if result.intent == "out_of_scope" or result.scope_score < threshold:
        return "out_of_scope"

    # Execute tools
    if result.intent == "execute" and result.tool_calls:
        return "execute"

    # Intent is "direct" -- safety net: if we have ungraded retrieved chunks,
    # route to evaluate instead of skipping straight to generate
    retrieved_chunks = state.get("retrieved_chunks", [])
    relevant_chunks = state.get("relevant_chunks", [])
    if retrieved_chunks and not relevant_chunks:
        return "evaluate"

    return "generate"


def route_after_executor(state: AgentState) -> str:
    """Route after tool execution.

    Returns:
        - "confirm": If a tool triggered HITL pause (propose_ingest)
        - "evaluate": If retrieve_chunks was called and succeeded
        - "classify": Otherwise, go back to classify for next decision
    """
    if state.get("pause_reason"):
        return "confirm"

    last_executed = state.get("last_executed_tools", [])

    if not last_executed:
        return "classify"

    # Check if retrieve_chunks was in current batch and succeeded
    if RETRIEVE_CHUNKS in last_executed:
        for t in reversed(state.get("tool_history", [])):
            if t.tool_name == RETRIEVE_CHUNKS:
                return "evaluate" if t.success else "classify"

    return "classify"


def route_after_eval(state: AgentState) -> str:
    """Route after batch evaluation.

    Returns:
        - "generate": Chunks are sufficient or max iterations reached
        - "classify": Insufficient, rewrite and retry
    """
    evaluation = state.get("evaluation_result")
    if not evaluation:
        return "generate"

    if evaluation.sufficient:
        return "generate"

    max_iterations = state.get("max_iterations", 5)
    iteration = state.get("iteration", 0)

    # Max iterations reached -- generate with what we have
    if iteration >= max_iterations:
        return "generate"

    # Insufficient and iterations remain -- rewrite loop
    return "classify"
