"""Tier 2: Citation accuracy (real LLM + mocked tool execution).

Runs graph.ainvoke() and scores whether the answer correctly cites
the papers present in the retrieval context without fabricating citations.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from .fixtures.citation_scenarios import CITATION_SCENARIOS, CitationScenario
from .helpers import (
    build_initial_state,
    extract_answer,
    extract_retrieval_context,
    make_tool_execute,
)


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

    with patch.object(
        ctx.tool_registry,
        "execute",
        side_effect=make_tool_execute(scenario.canned_chunks, scenario.canned_tool_outputs),
    ):
        final_state = await compiled_graph.ainvoke(state, eval_config)

    actual_output = extract_answer(final_state)
    retrieval_context = extract_retrieval_context(final_state)

    assert actual_output, f"[{scenario.id}] Graph produced empty answer"

    # If no relevant chunks survived grading, use raw tool outputs
    if not retrieval_context:
        tool_outputs = final_state.get("tool_outputs", [])
        retrieval_context = [str(out.get("data", "")) for out in tool_outputs if out.get("data")]

    # Fall back to raw canned chunks so the evaluator can verify the agent
    # did not fabricate citations from irrelevant context.
    if not retrieval_context and scenario.canned_chunks:
        retrieval_context = [
            c.get("chunk_text", "") for c in scenario.canned_chunks if c.get("chunk_text")
        ]

    if scenario.expected_arxiv_ids:
        expected_ids_str = ", ".join(scenario.expected_arxiv_ids)
        expected_titles_str = ", ".join(scenario.expected_titles)
        criteria = (
            "Evaluate the citation accuracy of an academic research assistant's response. "
            f"The response SHOULD reference these arXiv paper IDs: {expected_ids_str}. "
            f"The papers are titled: {expected_titles_str}. "
            "The response should: "
            "1) Mention or attribute information to the expected papers "
            "(by ID, title, or author), "
            "2) Not fabricate citations to papers that were not in the retrieval context, "
            "3) Correctly associate claims with their source papers."
        )
    else:
        criteria = (
            "Evaluate whether the response avoids fabricating citations. "
            "The retrieval context does NOT contain papers relevant to the query. "
            "The response should: "
            "1) NOT cite specific arXiv IDs, paper titles, or authors that are not "
            "present in the retrieval context, "
            "2) Acknowledge the lack of relevant sources or decline to answer rather "
            "than inventing references, "
            "3) Not attribute claims to non-existent papers."
        )

    test_case = LLMTestCase(
        input=scenario.query,
        actual_output=actual_output,
        retrieval_context=retrieval_context if retrieval_context else None,
    )

    eval_params = [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
    if retrieval_context:
        eval_params.append(LLMTestCaseParams.RETRIEVAL_CONTEXT)

    metric = GEval(
        name="Citation Accuracy",
        criteria=criteria,
        evaluation_params=eval_params,
        threshold=0.5,
    )

    assert_test(test_case, [metric])
