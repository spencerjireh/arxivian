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
    assert "list_papers" in result.tools_invoked, (
        f"Expected list_papers in tools_invoked, got: {result.tools_invoked}"
    )


@pytest.mark.inteval
async def test_arxiv_search_tool_invoked(agent_service: AgentService):
    """A search query should invoke the arxiv_search tool via real arXiv API."""
    result = await consume_stream(
        agent_service,
        "Search arXiv for papers about chain-of-thought prompting and list what you find.",
    )
    assert result.done_event is not None
    assert "arxiv_search" in result.tools_invoked, (
        f"Expected arxiv_search in tools_invoked, got: {result.tools_invoked}"
    )
