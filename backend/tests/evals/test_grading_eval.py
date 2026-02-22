"""Tier 1: Batch evaluation node accuracy (real LLM, direct node call).

Tests whether the evaluate_batch node correctly determines chunk set sufficiency
and triggers query rewrites when appropriate.
"""

from __future__ import annotations

import copy

import pytest

from src.services.agent_service.nodes.evaluate_batch import evaluate_batch_node

from .fixtures.grading_scenarios import GRADING_SCENARIOS, GradingScenario
from .helpers import build_initial_state


@pytest.mark.parametrize(
    "scenario",
    GRADING_SCENARIOS,
    ids=[s.id for s in GRADING_SCENARIOS],
)
async def test_batch_evaluation(
    scenario: GradingScenario,
    eval_config: dict,
) -> None:
    """Batch evaluation node should correctly assess chunk set sufficiency."""
    ctx = eval_config["configurable"]["context"]
    test_ctx = copy.copy(ctx)
    test_ctx.top_k = scenario.top_k
    test_config = {"configurable": {"context": test_ctx}}

    state = build_initial_state(
        query=scenario.query,
        original_query=scenario.query,
        retrieved_chunks=scenario.chunks,
        max_iterations=scenario.max_iterations,
    )
    state["iteration"] = scenario.iteration

    result = await evaluate_batch_node(state, test_config)

    evaluation = result["evaluation_result"]

    # Check sufficiency: if we expected all chunks to be relevant, the set should
    # be sufficient. If we expected few relevant chunks, it should be insufficient.
    expected_sufficient = len(scenario.expected_relevant_ids) >= scenario.top_k
    assert evaluation.sufficient == expected_sufficient, (
        f"[{scenario.id}] Expected sufficient={expected_sufficient}, "
        f"got sufficient={evaluation.sufficient}. Reasoning: {evaluation.reasoning}"
    )

    # Check rewrite behavior: if insufficient and iterations remain, expect rewrite
    if not expected_sufficient and scenario.expect_rewrite:
        has_rewrite = result.get("rewritten_query") is not None
        assert has_rewrite, (
            f"[{scenario.id}] Expected rewrite suggestion but got None"
        )
