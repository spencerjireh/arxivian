"""SSE event structure tests -- verify event ordering and completeness."""

from __future__ import annotations

import pytest

from src.services.agent_service import AgentService

from .helpers import consume_stream
from .scenarios import RETRIEVAL_SCENARIOS


@pytest.mark.inteval
@pytest.mark.parametrize(
    "scenario",
    RETRIEVAL_SCENARIOS[:2],
    ids=[s.id for s in RETRIEVAL_SCENARIOS[:2]],
)
async def test_sse_event_sequence(agent_service: AgentService, scenario):
    """STATUS events appear before CONTENT, METADATA after CONTENT, ends with DONE."""
    result = await consume_stream(agent_service, scenario.query)

    types = result.event_types

    # Must contain at least one STATUS, one CONTENT, METADATA, DONE
    assert "status" in types, f"No STATUS events. Got: {types}"
    assert "content" in types, f"No CONTENT events. Got: {types}"
    assert "metadata" in types, f"No METADATA event. Got: {types}"
    assert "done" in types, f"No DONE event. Got: {types}"

    # STATUS must appear before CONTENT
    first_status = types.index("status")
    first_content = types.index("content")
    assert first_status < first_content, "STATUS should precede CONTENT"

    # METADATA must appear after last CONTENT
    last_content = len(types) - 1 - types[::-1].index("content")
    metadata_idx = types.index("metadata")
    assert metadata_idx > last_content, "METADATA should follow all CONTENT"

    # DONE must be last
    assert types[-1] == "done", f"Last event should be DONE, got: {types[-1]}"


@pytest.mark.inteval
async def test_sse_no_error_events(agent_service: AgentService):
    """A valid in-scope query should produce no ERROR events."""
    result = await consume_stream(
        agent_service,
        "What is the Transformer architecture?",
    )
    assert len(result.error_events) == 0, (
        f"Expected no errors, got: {[e.data for e in result.error_events]}"
    )
    assert result.done_event is not None, "Stream should end with DONE"
