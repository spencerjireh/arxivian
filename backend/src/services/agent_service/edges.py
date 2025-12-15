"""Conditional edge functions for graph routing."""

from src.schemas.langgraph_state import AgentState


def continue_after_guardrail(state: AgentState) -> str:
    """Route based on guardrail score."""
    score = state["guardrail_result"].score
    threshold = state["metadata"].get("guardrail_threshold", 75)

    if score >= threshold:
        return "continue"
    else:
        return "out_of_scope"


def continue_after_grading(state: AgentState) -> str:
    """Route based on grading results."""
    return state["routing_decision"]
