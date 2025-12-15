"""Out of scope handler node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext
from ..prompts import get_out_of_scope_message


async def out_of_scope_node(state: AgentState, context: AgentContext) -> dict:
    """Handle out-of-scope queries."""
    guardrail_result = state["guardrail_result"]

    message = get_out_of_scope_message(
        state["original_query"], guardrail_result.score, guardrail_result.reasoning
    )

    state["messages"].append(AIMessage(content=message))
    return state
