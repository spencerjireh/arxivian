"""Tier 1: Out-of-scope response quality (real LLM, direct node call).

Tests whether the out_of_scope_node generates polite, helpful responses
that explain the system's arXiv focus and suggest academic angles.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.schemas.langgraph_state import ClassificationResult
from src.services.agent_service.nodes.out_of_scope import out_of_scope_node

from .fixtures.out_of_scope_scenarios import OUT_OF_SCOPE_SCENARIOS, OutOfScopeScenario
from .helpers import build_initial_state


@pytest.mark.parametrize(
    "scenario",
    OUT_OF_SCOPE_SCENARIOS,
    ids=[s.id for s in OUT_OF_SCOPE_SCENARIOS],
)
async def test_out_of_scope_response_quality(
    scenario: OutOfScopeScenario,
    eval_config: dict,
) -> None:
    """Out-of-scope node should produce polite, focused rejection responses."""
    state = build_initial_state(
        query=scenario.query,
        original_query=scenario.query,
        conversation_history=scenario.conversation_history,
    )
    state["classification_result"] = ClassificationResult(
        intent="out_of_scope",
        scope_score=scenario.guardrail_score,
        reasoning=scenario.guardrail_reasoning,
    )

    result = await out_of_scope_node(state, eval_config)

    answer = result["messages"][0].content
    assert answer, f"[{scenario.id}] Out-of-scope node produced empty response"

    has_history = bool(scenario.conversation_history)
    criteria = (
        "Evaluate the quality of an out-of-scope response from an academic research assistant. "
        "The response should: "
        "1) Be polite and not dismissive, "
        "2) Explain that the system focuses on academic research papers from arXiv, "
        "3) Suggest a relevant academic research angle if possible, "
    )
    if has_history:
        criteria += "4) Reference or acknowledge the prior conversation context, "
    criteria += "and be concise (2-3 sentences)."

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=answer,
    )

    metric = GEval(
        name="Out-of-Scope Response Quality",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.25,
    )

    assert_test(test_case, [metric])
