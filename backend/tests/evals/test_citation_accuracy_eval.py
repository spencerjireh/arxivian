"""Tier 2: Citation accuracy (real LLM + mocked tool execution).

Runs graph.ainvoke() and scores whether the answer correctly cites
the papers present in the retrieval context without fabricating citations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.services.agent_service.tools import ToolResult

from .fixtures.citation_scenarios import CITATION_SCENARIOS, CitationScenario
from .helpers import build_initial_state, extract_answer, extract_retrieval_context


def _make_tool_execute(scenario: CitationScenario) -> AsyncMock:
    """Build a mock for ToolRegistry.execute that returns canned data."""

    async def _execute(name: str, **kwargs) -> ToolResult:
        if name == "retrieve_chunks":
            return ToolResult(success=True, data=scenario.canned_chunks, tool_name=name)
        for out in scenario.canned_tool_outputs:
            if out["tool_name"] == name:
                return ToolResult(success=True, data=out["data"], tool_name=name)
        return ToolResult(success=True, data=[], tool_name=name)

    return AsyncMock(side_effect=_execute)


@pytest.mark.parametrize(
    "scenario",
    CITATION_SCENARIOS,
    ids=[s.id for s in CITATION_SCENARIOS],
)
async def test_citation_accuracy(
    scenario: CitationScenario,
    eval_config: dict,
    compiled_graph,
) -> None:
    """Full graph run should produce answers with accurate citations."""
    ctx = eval_config["configurable"]["context"]
    state = build_initial_state(
        query=scenario.query,
        conversation_history=scenario.conversation_history,
        max_iterations=ctx.max_iterations,
    )

    with patch.object(ctx.tool_registry, "execute", side_effect=_make_tool_execute(scenario)):
        final_state = await compiled_graph.ainvoke(state, eval_config)

    actual_output = extract_answer(final_state)
    retrieval_context = extract_retrieval_context(final_state)

    assert actual_output, f"[{scenario.id}] Graph produced empty answer"

    # If no relevant chunks survived grading, use raw tool outputs
    if not retrieval_context:
        tool_outputs = final_state.get("tool_outputs", [])
        retrieval_context = [str(out.get("data", "")) for out in tool_outputs if out.get("data")]

    expected_ids_str = ", ".join(scenario.expected_arxiv_ids)
    expected_titles_str = ", ".join(scenario.expected_titles)

    criteria = (
        "Evaluate the citation accuracy of an academic research assistant's response. "
        f"The response SHOULD reference these arXiv paper IDs: {expected_ids_str}. "
        f"The papers are titled: {expected_titles_str}. "
        "The response should: "
        "1) Mention or attribute information to the expected papers (by ID, title, or author), "
        "2) Not fabricate citations to papers that were not in the retrieval context, "
        "3) Correctly associate claims with their source papers."
    )

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=actual_output,
        retrieval_context=retrieval_context if retrieval_context else None,
    )

    metric = GEval(
        name="Citation Accuracy",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,
    )

    assert_test(test_case, [metric])
