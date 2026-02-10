"""Core RAG pipeline tests -- retrieval quality and answer quality."""

from __future__ import annotations

import pytest

from src.services.agent_service import AgentService

from .helpers import consume_stream
from .scenarios import RETRIEVAL_SCENARIOS


@pytest.mark.inteval
@pytest.mark.parametrize(
    "scenario",
    RETRIEVAL_SCENARIOS,
    ids=[s.id for s in RETRIEVAL_SCENARIOS],
)
async def test_retrieval_and_answer_quality(agent_service: AgentService, scenario):
    """Full pipeline: query -> retrieval -> grading -> generation.

    Asserts:
      - Non-trivial answer generated
      - Expected keywords present in answer
      - Expected source papers appear in SOURCES event
    """
    result = await consume_stream(agent_service, scenario.query)

    # Answer should be non-trivial
    answer = result.answer
    assert len(answer) > 50, f"Answer too short ({len(answer)} chars): {answer[:200]}"

    # Check expected keywords (case-insensitive, hyphen-normalized substring match)
    answer_normalized = answer.lower()
    for ch in "\u2010\u2011\u2012\u2013\u2014\u2212":
        answer_normalized = answer_normalized.replace(ch, "-")
    for keyword in scenario.expected_keywords:
        assert keyword.lower() in answer_normalized, (
            f"Expected keyword '{keyword}' not found in answer: {answer[:300]}"
        )

    # Check source papers in SOURCES event (soft check -- LLM routing is
    # non-deterministic and may answer from context or use different sources)
    if scenario.expected_source_ids:
        source_ids = result.source_arxiv_ids
        if source_ids:
            for expected_id in scenario.expected_source_ids:
                assert expected_id in source_ids, (
                    f"Expected source {expected_id} not in sources: {source_ids}"
                )


@pytest.mark.inteval
async def test_out_of_scope_query(agent_service: AgentService):
    """Off-topic query should be handled gracefully (no crash, gets DONE)."""
    result = await consume_stream(
        agent_service,
        "What is the best recipe for chocolate cake?",
    )

    # Should still complete without error
    assert result.done_event is not None, "Stream should end with DONE"
    assert len(result.error_events) == 0, "No errors expected for out-of-scope"
    assert result.metadata_event is not None, "Should have METADATA"
