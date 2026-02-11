"""Tier 1: Grading node relevance evaluation (real LLM, direct node call).

Tests whether the grading node correctly identifies relevant vs irrelevant
chunks and triggers query rewrites when appropriate.
"""

from __future__ import annotations

import pytest

from src.services.agent_service.nodes.grading import grade_documents_node

from .fixtures.grading_scenarios import GRADING_SCENARIOS, GradingScenario
from .helpers import build_initial_state


@pytest.mark.parametrize(
    "scenario",
    GRADING_SCENARIOS,
    ids=[s.id for s in GRADING_SCENARIOS],
)
async def test_grading_relevance(
    scenario: GradingScenario,
    eval_config: dict,
) -> None:
    """Grading node should correctly classify chunk relevance and trigger rewrites."""
    ctx = eval_config["configurable"]["context"]
    original_top_k = ctx.top_k

    try:
        ctx.top_k = scenario.top_k

        state = build_initial_state(
            query=scenario.query,
            original_query=scenario.query,
            retrieved_chunks=scenario.chunks,
            max_iterations=scenario.max_iterations,
        )
        state["iteration"] = scenario.iteration

        result = await grade_documents_node(state, eval_config)

        # Check relevant chunk IDs
        actual_ids = sorted(c["chunk_id"] for c in result["relevant_chunks"])
        expected_ids = sorted(scenario.expected_relevant_ids)
        assert actual_ids == expected_ids, (
            f"[{scenario.id}] Expected relevant IDs {expected_ids}, got {actual_ids}"
        )

        # Check rewrite behavior
        has_rewrite = result["rewritten_query"] is not None
        assert has_rewrite == scenario.expect_rewrite, (
            f"[{scenario.id}] Expected rewrite={scenario.expect_rewrite}, "
            f"got rewritten_query={'present' if has_rewrite else 'None'}"
        )
    finally:
        ctx.top_k = original_top_k
