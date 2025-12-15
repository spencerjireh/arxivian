"""Out of scope handler node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext
from ..prompts import get_out_of_scope_message


async def out_of_scope_node(state: AgentState, context: AgentContext) -> AgentState:
    """Handle out-of-scope queries."""
    guardrail_result = state.get("guardrail_result")
    original_query = state.get("original_query") or ""

    if guardrail_result:
        message = get_out_of_scope_message(
            original_query, guardrail_result.score, guardrail_result.reasoning
        )
    else:
        message = "I'm sorry, but I can only answer questions related to AI/ML research papers."

    state["messages"].append(AIMessage(content=message))
    return state
