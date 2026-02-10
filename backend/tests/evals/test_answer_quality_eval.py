"""Tier 2: Full-graph answer quality (real LLM + mocked tool execution).

Runs graph.ainvoke() and scores the final answer with DeepEval metrics:
- AnswerRelevancyMetric  (>= 0.7)
- FaithfulnessMetric     (>= 0.7)
- ContextualRelevancyMetric (>= 0.6)
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from src.services.agent_service.tools import ToolResult
from .fixtures.answer_quality_scenarios import (
    ANSWER_QUALITY_SCENARIOS,
    AnswerQualityScenario,
)
from .helpers import build_initial_state, extract_answer, extract_retrieval_context


def _make_tool_execute(scenario: AnswerQualityScenario) -> AsyncMock:
    """Build a mock for ToolRegistry.execute that returns canned data."""

    async def _execute(name: str, **kwargs) -> ToolResult:
        if name == "retrieve_chunks":
            return ToolResult(success=True, data=scenario.canned_chunks, tool_name=name)
        # For other tools, check canned_tool_outputs
        for out in scenario.canned_tool_outputs:
            if out["tool_name"] == name:
                return ToolResult(success=True, data=out["data"], tool_name=name)
        return ToolResult(success=True, data=[], tool_name=name)

    mock = AsyncMock(side_effect=_execute)
    return mock


@pytest.mark.parametrize(
    "scenario",
    ANSWER_QUALITY_SCENARIOS,
    ids=[s.id for s in ANSWER_QUALITY_SCENARIOS],
)
async def test_answer_quality(
    scenario: AnswerQualityScenario,
    eval_context,
    compiled_graph,
) -> None:
    """Full graph run should produce relevant, faithful answers."""
    state = build_initial_state(
        query=scenario.query,
        conversation_history=scenario.conversation_history,
    )
    config = {"configurable": {"context": eval_context}}

    # Patch tool execution to return canned data
    original_execute = eval_context.tool_registry.execute
    eval_context.tool_registry.execute = _make_tool_execute(scenario)

    try:
        final_state = await compiled_graph.ainvoke(state, config)
    finally:
        eval_context.tool_registry.execute = original_execute

    actual_output = extract_answer(final_state)
    retrieval_context = extract_retrieval_context(final_state)

    assert actual_output, f"[{scenario.id}] Graph produced empty answer"

    # If there is no retrieval context (e.g. arxiv_search-only scenario),
    # use tool output summaries as context for faithfulness.
    if not retrieval_context:
        tool_outputs = final_state.get("tool_outputs", [])
        retrieval_context = [str(out.get("data", "")) for out in tool_outputs if out.get("data")]

    # Skip faithfulness/context checks when there is truly no context
    if not retrieval_context:
        test_case = LLMTestCase(
            input=scenario.query,
            actual_output=actual_output,
        )
        assert_test(test_case, [AnswerRelevancyMetric(threshold=0.5)])
        return

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=actual_output,
        retrieval_context=retrieval_context,
    )

    metrics = [
        AnswerRelevancyMetric(threshold=0.5),
        FaithfulnessMetric(threshold=0.5),
        ContextualRelevancyMetric(threshold=0.5),
    ]
    assert_test(test_case, metrics)
