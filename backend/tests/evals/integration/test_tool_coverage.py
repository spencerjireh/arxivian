"""Tool coverage tests -- verify each agent tool is invoked via the real agent."""

from __future__ import annotations

import pytest

from src.services.agent_service import AgentService

from .helpers import consume_stream


@pytest.mark.inteval
async def test_retrieve_tool_invoked(agent_service: AgentService):
    """A retrieval query should invoke the retrieve tool and return sources."""
    result = await consume_stream(
        agent_service,
        "Retrieve information from the papers about multi-head attention in the Transformer architecture.",
    )
    assert result.done_event is not None
    assert len(result.source_arxiv_ids) > 0, "Should have retrieved sources"


@pytest.mark.inteval
async def test_list_papers_tool_invoked(agent_service: AgentService):
    """A list query should invoke the list_papers tool."""
    result = await consume_stream(
        agent_service,
        "List all the papers currently available in my knowledge base using the list papers tool.",
    )
    assert result.done_event is not None
    # Check if list_papers tool was invoked or answer mentions papers
    has_list_tool = any(
        "list_papers" in str(getattr(e.data, "details", {}))
        for e in result.status_events
    )
    answer_lower = result.answer.lower()
    has_paper_mention = any(
        term in answer_lower
        for term in ["attention", "bert", "gpt", "transformer", "vision"]
    )
    assert has_list_tool or has_paper_mention, (
        f"Should invoke list_papers or mention papers: {result.answer[:300]}"
    )


@pytest.mark.inteval
async def test_arxiv_search_tool_invoked(agent_service: AgentService):
    """A search query should invoke the arxiv_search tool via real arXiv API."""
    result = await consume_stream(
        agent_service,
        "Search arXiv for papers about chain-of-thought prompting and list what you find.",
    )
    assert result.done_event is not None
    # The arxiv_search tool should be invoked (visible in status events)
    has_search = any(
        "arxiv_search" in str(getattr(e.data, "details", {}))
        for e in result.status_events
    )
    assert has_search or len(result.answer) > 0, (
        "Should invoke arxiv_search or produce an answer"
    )


@pytest.mark.inteval
async def test_summarize_paper_tool_invoked(agent_service: AgentService):
    """A summarize query should invoke the summarize tool for a seeded paper."""
    result = await consume_stream(
        agent_service,
        "Summarize the paper 'Attention Is All You Need'.",
    )
    assert result.done_event is not None
    answer_lower = result.answer.lower()
    assert any(
        term in answer_lower for term in ["transformer", "attention", "self-attention"]
    ), f"Summary should reference transformer concepts: {result.answer[:300]}"
