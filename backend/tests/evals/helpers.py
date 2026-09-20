"""Shared utilities for eval tests."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.tools import ToolResult

from .fixtures.canned_data import CITATION_RESULTS


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
        "classification_result": None,
        "evaluation_result": None,
        "tool_history": tool_history or [],
        "last_executed_tools": [],
        "retrieval_attempts": 0,
        "retrieved_chunks": retrieved_chunks or [],
        "relevant_chunks": [],
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
    mock.retrieve_within_paper = AsyncMock(return_value=canned_chunks)
    return mock


def make_tool_execute(
    canned_chunks: list[dict],
    canned_tool_outputs: list[dict] | None = None,
) -> Callable[..., Coroutine[Any, Any, ToolResult]]:
    """Build a side_effect function for ToolRegistry.execute that returns canned data.

    For ``retrieve_chunks`` calls, returns *canned_chunks*.
    For other tools, matches by ``tool_name`` in *canned_tool_outputs* and
    honours the optional ``success`` flag (defaults to ``True``).
    Anything unmatched falls back to an empty successful result.
    """
    outputs = canned_tool_outputs or []

    async def _execute(name: str, **kwargs: object) -> ToolResult:
        if name == "retrieve_chunks":
            return ToolResult(success=True, data=canned_chunks, tool_name=name)
        for out in outputs:
            if out["tool_name"] == name:
                return ToolResult(
                    success=out.get("success", True),
                    data=out.get("data"),
                    error=out.get("error"),
                    tool_name=name,
                )
        return ToolResult(success=True, data=[], tool_name=name)

    return _execute


def make_tool_result(tool_name: str, data: object, success: bool = True) -> ToolResult:
    """Create a ToolResult with canned data."""
    return ToolResult(success=success, data=data, tool_name=tool_name)


@dataclass
class ServiceMocks:
    """Holds all mocked external services with pre-configured return values."""

    search_service: AsyncMock = field(default_factory=AsyncMock)
    paper_repository: AsyncMock = field(default_factory=AsyncMock)
    semantic_scholar_client: AsyncMock = field(default_factory=AsyncMock)


class ServiceMockBuilder:
    """Fluent builder for ServiceMocks with sensible defaults."""

    def __init__(self) -> None:
        self._search_results: list[dict] = []
        self._citation_results: dict = CITATION_RESULTS

    def with_search_results(self, chunks: list[dict]) -> ServiceMockBuilder:
        self._search_results = chunks
        return self

    def with_citations(self, result: dict) -> ServiceMockBuilder:
        self._citation_results = result
        return self

    def build(self) -> ServiceMocks:
        search_service = AsyncMock()
        search_service.retrieve_within_paper = AsyncMock(return_value=self._search_results)

        paper_repository = AsyncMock()
        paper_repository.get_citations = AsyncMock(return_value=self._citation_results)

        semantic_scholar_client = AsyncMock()
        semantic_scholar_client.get_citation_metrics = AsyncMock(return_value=None)

        return ServiceMocks(
            search_service=search_service,
            paper_repository=paper_repository,
            semantic_scholar_client=semantic_scholar_client,
        )
