"""Tier 1: Classify-and-route classification accuracy (real LLM, direct node call).

No DeepEval metrics here -- using an LLM to judge the classification LLM would be
circular.  We assert boolean classification directly.
"""

from __future__ import annotations

import pytest

from .fixtures.guardrail_scenarios import GUARDRAIL_SCENARIOS, GuardrailScenario
from .helpers import build_initial_state
from src.services.agent_service.nodes.classify_and_route import classify_and_route_node


@pytest.mark.parametrize(
    "scenario",
    GUARDRAIL_SCENARIOS,
    ids=[s.id for s in GUARDRAIL_SCENARIOS],
)
async def test_guardrail_classification(
    scenario: GuardrailScenario,
    eval_config: dict,
) -> None:
    """Classify-and-route should correctly classify in-scope vs out-of-scope queries."""
    state = build_initial_state(
        query=scenario.query,
        conversation_history=scenario.conversation_history,
    )
    result = await classify_and_route_node(state, eval_config)

    classification = result["classification_result"]
    threshold = eval_config["configurable"]["context"].guardrail_threshold
    actual_in_scope = classification.scope_score >= threshold

    assert actual_in_scope == scenario.expected_in_scope, (
        f"[{scenario.id}] Expected in_scope={scenario.expected_in_scope}, "
        f"got score={classification.scope_score} (threshold={threshold}). "
        f"Reasoning: {classification.reasoning}"
    )
