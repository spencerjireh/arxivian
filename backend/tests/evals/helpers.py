"""Shared utilities for eval tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.tools import ToolResult


def build_initial_state(
    query: str,
    conversation_history: list[dict] | None = None,
    original_query: str | None = None,
    tool_history: list | None = None,
    retrieved_chunks: list[dict] | None = None,
    max_iterations: int = 5,
) -> AgentState:
    """Build a minimal AgentState for graph invocation."""
    return {
        "messages": [HumanMessage(content=query)],
        "original_query": original_query,
        "rewritten_query": None,
        "status": "running",
        "iteration": 0,
        "max_iterations": max_iterations,
        "router_decision": None,
        "tool_history": tool_history or [],
        "last_executed_tools": [],
        "pause_reason": None,
        "retrieval_attempts": 0,
        "guardrail_result": None,
        "retrieved_chunks": retrieved_chunks or [],
        "relevant_chunks": [],
        "grading_results": [],
        "tool_outputs": [],
        "metadata": {
            "guardrail_threshold": 75,
            "top_k": 3,
            "reasoning_steps": [],
        },
        "conversation_history": conversation_history or [],
        "session_id": None,
    }


def extract_answer(final_state: dict) -> str:
    """Extract the final assistant answer from graph output state."""
    messages = final_state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def extract_retrieval_context(final_state: dict) -> list[str]:
    """Extract retrieval context texts from the final state.

    Uses only relevant_chunks (post-grading), not retrieved_chunks,
    since the generation node only sees graded-relevant chunks.
    """
    chunks = final_state.get("relevant_chunks") or []
    return [c.get("chunk_text", "") for c in chunks if c.get("chunk_text")]


def extract_tools_called(final_state: dict) -> list[str]:
    """Extract list of tool names called during the run."""
    return [t.tool_name for t in final_state.get("tool_history", [])]


def make_retrieve_mock(canned_chunks: list[dict]) -> AsyncMock:
    """Create a mock search service that returns canned chunks."""
    mock = AsyncMock()
    mock.hybrid_search = AsyncMock(return_value=canned_chunks)
    return mock


def make_tool_result(tool_name: str, data: object, success: bool = True) -> ToolResult:
    """Create a ToolResult with canned data."""
    return ToolResult(success=success, data=data, tool_name=tool_name)
