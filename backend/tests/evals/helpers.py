"""Shared utilities for eval tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.tools import ToolResult
from .fixtures.canned_data import (
    ARXIV_SEARCH_RESULTS,
    CITATION_RESULTS,
    LIST_PAPERS_RESULTS,
)


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


@dataclass
class ServiceMocks:
    """Holds all mocked external services with pre-configured return values."""

    search_service: AsyncMock = field(default_factory=AsyncMock)
    ingest_service: AsyncMock = field(default_factory=AsyncMock)
    arxiv_client: AsyncMock = field(default_factory=AsyncMock)
    paper_repository: AsyncMock = field(default_factory=AsyncMock)


class ServiceMockBuilder:
    """Fluent builder for ServiceMocks with sensible defaults."""

    def __init__(self) -> None:
        self._search_results: list[dict] = []
        self._list_papers_result: dict = LIST_PAPERS_RESULTS
        self._arxiv_results: dict = ARXIV_SEARCH_RESULTS
        self._citation_results: dict = CITATION_RESULTS

    def with_search_results(self, chunks: list[dict]) -> ServiceMockBuilder:
        self._search_results = chunks
        return self

    def with_list_papers(self, result: dict) -> ServiceMockBuilder:
        self._list_papers_result = result
        return self

    def with_arxiv_results(self, result: dict) -> ServiceMockBuilder:
        self._arxiv_results = result
        return self

    def with_citations(self, result: dict) -> ServiceMockBuilder:
        self._citation_results = result
        return self

    def build(self) -> ServiceMocks:
        search_service = AsyncMock()
        search_service.hybrid_search = AsyncMock(return_value=self._search_results)

        ingest_service = AsyncMock()
        ingest_service.list_papers = AsyncMock(return_value=self._list_papers_result)

        arxiv_client = AsyncMock()
        arxiv_client.search = AsyncMock(return_value=self._arxiv_results)

        paper_repository = AsyncMock()
        paper_repository.get_citations = AsyncMock(return_value=self._citation_results)
        paper_repository.get_existing_arxiv_ids = AsyncMock(return_value=set())

        return ServiceMocks(
            search_service=search_service,
            ingest_service=ingest_service,
            arxiv_client=arxiv_client,
            paper_repository=paper_repository,
        )
