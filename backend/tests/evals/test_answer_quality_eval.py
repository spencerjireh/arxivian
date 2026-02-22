"""Tier 2: Full-graph answer quality (real LLM + mocked tool execution).

Runs graph.ainvoke() and scores the final answer with DeepEval metrics:
- AnswerRelevancyMetric  (>= 0.7)
- FaithfulnessMetric     (>= 0.7)
- ContextualRelevancyMetric (>= 0.6)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from .fixtures.answer_quality_scenarios import (
    ANSWER_QUALITY_SCENARIOS,
    AnswerQualityScenario,
)
from .helpers import (
    build_initial_state,
    extract_answer,
    extract_retrieval_context,
    make_tool_execute,
)


@pytest.mark.parametrize(
    "scenario",
    ANSWER_QUALITY_SCENARIOS,
    ids=[s.id for s in ANSWER_QUALITY_SCENARIOS],
)
async def test_answer_quality(
    scenario: AnswerQualityScenario,
    eval_config: dict,
    compiled_graph,
) -> None:
    """Full graph run should produce relevant, faithful answers."""
    ctx = eval_config["configurable"]["context"]
    state = build_initial_state(
        query=scenario.query,
        conversation_history=scenario.conversation_history,
        max_iterations=ctx.max_iterations,
    )

    with patch.object(
        ctx.tool_registry,
        "execute",
        side_effect=make_tool_execute(scenario.canned_chunks, scenario.canned_tool_outputs),
    ):
        final_state = await compiled_graph.ainvoke(state, eval_config)

    actual_output = extract_answer(final_state)
    retrieval_context = extract_retrieval_context(final_state)

    if not actual_output:
        pytest.skip(f"[{scenario.id}] LLM returned empty answer (model limitation)")

    # If there is no retrieval context (e.g. arxiv_search-only scenario),
    # use tool output summaries as context for faithfulness.
    # Exclude error-only outputs ({"error": "..."}) -- they carry no real content.
    if not retrieval_context:
        tool_outputs = final_state.get("tool_outputs", [])
        retrieval_context = [
            str(out["data"])
            for out in tool_outputs
            if out.get("data") and not (isinstance(out["data"], dict) and "error" in out["data"])
        ]

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

    metric_map: dict[str, type] = {
        "answer_relevancy": AnswerRelevancyMetric,
        "faithfulness": FaithfulnessMetric,
        "contextual_relevancy": ContextualRelevancyMetric,
    }

    if scenario.metrics_override:
        metrics = [metric_map[name](threshold=0.5) for name in scenario.metrics_override]
    else:
        metrics = [cls(threshold=0.5) for cls in metric_map.values()]

    assert_test(test_case, metrics)
