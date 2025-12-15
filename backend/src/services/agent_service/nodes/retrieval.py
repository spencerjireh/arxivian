"""Retrieval node for creating tool calls."""

import uuid
from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext


async def retrieve_node(state: AgentState, context: AgentContext) -> AgentState:
    """
    Create tool call for document retrieval.

    LangGraph's ToolNode will execute the actual retrieval.
    """
    query = state.get("rewritten_query") or state["original_query"]

    tool_call_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "retrieve_chunks",
                "args": {"query": query, "top_k": context.top_k * 2},  # Get extra for grading
                "id": f"call_{uuid.uuid4()}",
            }
        ],
    )

    state["messages"].append(tool_call_message)
    state["retrieval_attempts"] += 1
    state["metadata"]["reasoning_steps"].append(
        f"Retrieved documents (attempt {state['retrieval_attempts']})"
    )

    return state
