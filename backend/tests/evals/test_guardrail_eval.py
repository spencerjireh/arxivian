"""Tier 1: Guardrail classification accuracy (real LLM, direct node call).

No DeepEval metrics here -- using an LLM to judge the guardrail LLM would be
circular.  We assert boolean classification directly.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState
from .fixtures.guardrail_scenarios import GUARDRAIL_SCENARIOS, GuardrailScenario
from src.services.agent_service.nodes.guardrail import guardrail_node


def _build_guardrail_state(scenario: GuardrailScenario) -> AgentState:
    return {
        "messages": [HumanMessage(content=scenario.query)],
        "original_query": None,
        "rewritten_query": None,
        "status": "running",
        "iteration": 0,
        "max_iterations": 5,
        "router_decision": None,
        "tool_history": [],
        "last_executed_tools": [],
        "pause_reason": None,
        "retrieval_attempts": 0,
        "guardrail_result": None,
        "retrieved_chunks": [],
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
    GUARDRAIL_SCENARIOS,
    ids=[s.id for s in GUARDRAIL_SCENARIOS],
)
async def test_guardrail_classification(
    scenario: GuardrailScenario,
    eval_config: dict,
) -> None:
    """Guardrail should correctly classify in-scope vs out-of-scope queries."""
    state = _build_guardrail_state(scenario)
    result = await guardrail_node(state, eval_config)

    guardrail = result["guardrail_result"]
    threshold = eval_config["configurable"]["context"].guardrail_threshold
    actual_in_scope = guardrail.score >= threshold

    assert actual_in_scope == scenario.expected_in_scope, (
        f"[{scenario.id}] Expected in_scope={scenario.expected_in_scope}, "
        f"got score={guardrail.score} (threshold={threshold}). "
        f"Reasoning: {guardrail.reasoning}"
    )
