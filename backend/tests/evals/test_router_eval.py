"""Tier 1: Router tool selection accuracy (real LLM, direct node call).

Uses DeepEval ToolCorrectnessMetric to score whether the router picks
the right tools for each query.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall

from src.services.agent_service.nodes.router import router_node

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
    """Router should select the correct tools for each query type."""
    state = build_initial_state(
        query=scenario.query,
        original_query=scenario.query,
        conversation_history=scenario.conversation_history,
        tool_history=scenario.tool_history,
        retrieved_chunks=scenario.available_chunks,
    )
    result = await router_node(state, eval_config)

    decision = result["router_decision"]

    # Check action type
    assert decision.action == scenario.expected_action, (
        f"[{scenario.id}] Expected action={scenario.expected_action}, "
        f"got action={decision.action}. Reasoning: {decision.reasoning}"
    )

    if not scenario.expected_tools:
        # "generate" action -- no tools expected
        return

    # Build DeepEval test case for tool correctness
    actual_tools = [
        ToolCall(name=tc.tool_name)
        for tc in decision.tool_calls
    ]
    expected_tools = [
        ToolCall(name=name)
        for name in scenario.expected_tools
    ]

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=decision.reasoning,
        tools_called=actual_tools,
        expected_tools=expected_tools,
    )

    metric = ToolCorrectnessMetric(threshold=0.5)
    assert_test(test_case, [metric])
