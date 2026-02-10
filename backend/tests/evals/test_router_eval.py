"""Tier 1: Router tool selection accuracy (real LLM, direct node call).

Uses DeepEval ToolCorrectnessMetric to score whether the router picks
the right tools for each query.
"""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall
from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState
from src.services.agent_service.nodes.router import router_node

from .fixtures.router_scenarios import ROUTER_SCENARIOS, RouterScenario


def _build_router_state(scenario: RouterScenario) -> AgentState:
    return {
        "messages": [HumanMessage(content=scenario.query)],
        "original_query": scenario.query,
        "rewritten_query": None,
        "status": "running",
        "iteration": 0,
        "max_iterations": 5,
        "router_decision": None,
        "tool_history": scenario.tool_history,
        "last_executed_tools": [],
        "pause_reason": None,
        "retrieval_attempts": 0,
        "guardrail_result": None,
        "retrieved_chunks": scenario.available_chunks,
        "relevant_chunks": [],
        "grading_results": [],
        "tool_outputs": [],
        "metadata": {
            "guardrail_threshold": 75,
            "top_k": 3,
            "reasoning_steps": [],
        },
        "conversation_history": scenario.conversation_history,
        "session_id": None,
    }


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
    state = _build_router_state(scenario)
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
