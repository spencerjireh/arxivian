"""Tier 1: Router tool selection accuracy (real LLM, direct node call).

Uses DeepEval ToolCorrectnessMetric to score whether the classify-and-route
node picks the right tools for each query.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall

from src.services.agent_service.nodes.classify_and_route import classify_and_route_node

from .fixtures.router_scenarios import ROUTER_SCENARIOS, RouterScenario
from .helpers import build_initial_state


@pytest.mark.parametrize(
    "scenario",
    ROUTER_SCENARIOS,
    ids=[s.id for s in ROUTER_SCENARIOS],
)
async def test_router_tool_selection(
    scenario: RouterScenario,
    eval_config: dict,
) -> None:
    """Classify-and-route should select the correct tools for each query type."""
    state = build_initial_state(
        query=scenario.query,
        original_query=scenario.query,
        conversation_history=scenario.conversation_history,
        tool_history=scenario.tool_history,
        retrieved_chunks=scenario.available_chunks,
    )
    result = await classify_and_route_node(state, eval_config)

    classification = result["classification_result"]

    # Map old expected_action to new intent
    expected_intent = (
        "execute" if scenario.expected_action == "execute_tools" else "direct"
    )
    assert classification.intent == expected_intent, (
        f"[{scenario.id}] Expected intent={expected_intent}, "
        f"got intent={classification.intent}. Reasoning: {classification.reasoning}"
    )

    if not scenario.expected_tools:
        # "direct" intent -- no tools expected
        return

    # Build DeepEval test case for tool correctness
    actual_tools = [
        ToolCall(name=tc.tool_name)
        for tc in classification.tool_calls
    ]
    expected_tools = [
        ToolCall(name=name)
        for name in scenario.expected_tools
    ]

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=classification.reasoning,
        tools_called=actual_tools,
        expected_tools=expected_tools,
    )

    metric = ToolCorrectnessMetric(threshold=0.5)
    assert_test(test_case, [metric])
