"""Tier 1: Guardrail classification accuracy (real LLM, direct node call).

No DeepEval metrics here -- using an LLM to judge the guardrail LLM would be
circular.  We assert boolean classification directly.
"""

from __future__ import annotations

import pytest

from .fixtures.guardrail_scenarios import GUARDRAIL_SCENARIOS, GuardrailScenario
from .helpers import build_initial_state
from src.services.agent_service.nodes.guardrail import guardrail_node


@pytest.mark.parametrize(
    "scenario",
    GUARDRAIL_SCENARIOS,
    ids=[s.id for s in GUARDRAIL_SCENARIOS],
)
async def test_guardrail_classification(
    scenario: GuardrailScenario,
    eval_config: dict,
) -> None:
    """Guardrail should correctly classify in-scope vs out-of-scope queries."""
    state = build_initial_state(
        query=scenario.query,
        conversation_history=scenario.conversation_history,
    )
    result = await guardrail_node(state, eval_config)

    guardrail = result["guardrail_result"]
    threshold = eval_config["configurable"]["context"].guardrail_threshold
    actual_in_scope = guardrail.score >= threshold

    assert actual_in_scope == scenario.expected_in_scope, (
        f"[{scenario.id}] Expected in_scope={scenario.expected_in_scope}, "
        f"got score={guardrail.score} (threshold={threshold}). "
        f"Reasoning: {guardrail.reasoning}"
    )
