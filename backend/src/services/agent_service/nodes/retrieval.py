"""Retrieval node for creating tool calls."""

import uuid
from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger
from ..context import AgentContext

log = get_logger(__name__)


async def retrieve_node(state: AgentState, context: AgentContext) -> AgentState:
    """
    Create tool call for document retrieval.

    LangGraph's ToolNode will execute the actual retrieval.
    """
    query = state.get("rewritten_query") or state["original_query"]
    attempt = state["retrieval_attempts"] + 1

    log.info(
        "retrieval started",
        query=query[:100] if query else "",
        attempt=attempt,
        top_k=context.top_k * 2,
    )

    tool_call_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "retrieve_chunks",
                "args": {"query": query, "top_k": context.top_k * 2},
                "id": f"call_{uuid.uuid4()}",
            }
        ],
    )

    state["messages"].append(tool_call_message)
    state["retrieval_attempts"] = attempt
    state["metadata"]["reasoning_steps"].append(f"Retrieved documents (attempt {attempt})")

    return state
