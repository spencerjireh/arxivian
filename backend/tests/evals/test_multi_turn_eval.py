"""Tier 2: Multi-turn conversation coherence (real LLM + mocked tools).

Runs sequential graph.ainvoke() calls, accumulating conversation history.
Scores the final answer with a custom GEval metric for coherence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.services.agent_service.tools import ToolResult
from .fixtures.multi_turn_scenarios import (
    MULTI_TURN_SCENARIOS,
    MultiTurnScenario,
    Turn,
)
from .helpers import build_initial_state, extract_answer


def _make_turn_execute(turn: Turn) -> AsyncMock:
    """Mock tool execution for a single turn."""

    async def _execute(name: str, **kwargs) -> ToolResult:
        if name == "retrieve_chunks":
            return ToolResult(success=True, data=turn.canned_chunks, tool_name=name)
        return ToolResult(success=True, data=[], tool_name=name)

    return AsyncMock(side_effect=_execute)


coherence_metric = GEval(
    name="Multi-turn Coherence",
    criteria=(
        "Evaluate whether the assistant's response is coherent with the "
        "conversation history. It should: "
        "1) Reference or build on information from prior turns when relevant, "
        "2) Not contradict earlier statements, "
        "3) Maintain topical continuity or smoothly transition topics, "
        "4) Provide a substantive answer to the current query."
    ),
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.3,
)


@pytest.mark.parametrize(
    "scenario",
    MULTI_TURN_SCENARIOS,
    ids=[s.id for s in MULTI_TURN_SCENARIOS],
)
async def test_multi_turn_coherence(
    scenario: MultiTurnScenario,
    eval_context,
    compiled_graph,
) -> None:
    """Sequential graph runs should produce coherent multi-turn conversations."""
    conversation_history: list[dict] = []
    answers: list[str] = []
    original_execute = eval_context.tool_registry.execute

    for i, turn in enumerate(scenario.turns):
        state = build_initial_state(
            query=turn.query,
            conversation_history=conversation_history,
        )
        config = {"configurable": {"context": eval_context}}

        eval_context.tool_registry.execute = _make_turn_execute(turn)

        try:
            final_state = await compiled_graph.ainvoke(state, config)
        finally:
            eval_context.tool_registry.execute = original_execute

        answer = extract_answer(final_state)
        assert answer, f"[{scenario.id}] Turn {i} produced empty answer"
        answers.append(answer)

        # Accumulate history for next turn
        conversation_history.append({"role": "user", "content": turn.query})
        conversation_history.append({"role": "assistant", "content": answer})

    # Score the final answer in context of the full conversation
    full_input = "\n".join(
        f"Turn {i+1} - User: {t.query}\nTurn {i+1} - Assistant: {answers[i]}"
        for i, t in enumerate(scenario.turns[:-1])
    )
    full_input += f"\nCurrent query: {scenario.turns[-1].query}"

    test_case = LLMTestCase(
        input=full_input,
        actual_output=answers[-1],
    )

    assert_test(test_case, [coherence_metric])
