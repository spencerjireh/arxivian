"""Tool coverage tests -- each scoped-agent tool is invoked via the real agent."""

from __future__ import annotations

import pytest

from .helpers import consume_stream


@pytest.mark.inteval
async def test_retrieve_tool_invoked(agent_for):
    """A content question should invoke retrieve_chunks and return sources."""
    agent_service = await agent_for("1706.03762")
    result = await consume_stream(
        agent_service, "Explain multi-head attention as described in this paper."
    )
    assert result.done_event is not None
    assert "retrieve_chunks" in result.tools_invoked, result.tools_invoked
    assert len(result.source_arxiv_ids) > 0, "Should have retrieved sources"


@pytest.mark.inteval
async def test_explore_citations_tool_invoked(agent_for):
    """A references question should invoke explore_citations."""
    agent_service = await agent_for("1706.03762")
    result = await consume_stream(
        agent_service, "What prior work does this paper cite and build upon?"
    )
    assert result.done_event is not None
    assert "explore_citations" in result.tools_invoked, result.tools_invoked
