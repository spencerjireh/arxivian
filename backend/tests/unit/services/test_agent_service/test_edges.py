"""Tests for edge routing functions."""

import pytest

from src.schemas.langgraph_state import (
    GuardrailScoring,
    RouterDecision,
    ToolCall,
    ToolExecution,
)
from src.services.agent_service.edges import (
    continue_after_guardrail,
    continue_after_grading,
    route_after_router,
    route_after_executor,
    route_after_grading_new,
)
from src.services.agent_service.tools import RETRIEVE_CHUNKS, LIST_PAPERS, ARXIV_SEARCH


class TestRouteAfterExecutor:
    """Tests for route_after_executor edge function."""

    def test_routes_to_grade_when_retrieve_chunks_in_current_batch(self):
        state = {
            "last_executed_tools": [RETRIEVE_CHUNKS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "grade"

    def test_routes_to_router_when_retrieve_chunks_in_history_but_not_current_batch(self):
        state = {
            "last_executed_tools": [LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "router"

    def test_routes_to_router_when_no_tools_executed(self):
        state = {"last_executed_tools": [], "tool_history": []}
        assert route_after_executor(state) == "router"

    def test_routes_to_router_when_last_executed_tools_missing(self):
        state = {"tool_history": []}
        assert route_after_executor(state) == "router"

    def test_routes_to_router_when_retrieve_chunks_failed(self):
        state = {
            "last_executed_tools": [RETRIEVE_CHUNKS],
            "tool_history": [
                ToolExecution(
                    tool_name=RETRIEVE_CHUNKS,
                    tool_args={},
                    success=False,
                    error="Connection failed",
                ),
            ],
        }
        assert route_after_executor(state) == "router"

    def test_routes_to_grade_with_parallel_execution_including_retrieve_chunks(self):
        state = {
            "last_executed_tools": [RETRIEVE_CHUNKS, LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "grade"

    def test_routes_to_router_with_other_tools_only(self):
        state = {
            "last_executed_tools": [ARXIV_SEARCH, LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=ARXIV_SEARCH, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "router"


class TestContinueAfterGuardrail:
    """Tests for continue_after_guardrail edge function."""

    def test_returns_continue_when_score_meets_default_threshold(self):
        state = {
            "guardrail_result": GuardrailScoring(
                score=80, reasoning="Query is relevant", is_in_scope=True
            ),
            "metadata": {},
        }
        assert continue_after_guardrail(state) == "continue"

    def test_returns_out_of_scope_when_score_below_default_threshold(self):
        state = {
            "guardrail_result": GuardrailScoring(
                score=70, reasoning="Query is borderline", is_in_scope=False
            ),
            "metadata": {},
        }
        assert continue_after_guardrail(state) == "out_of_scope"

    def test_returns_out_of_scope_when_guardrail_result_missing(self):
        state = {"guardrail_result": None, "metadata": {}}
        assert continue_after_guardrail(state) == "out_of_scope"

    def test_uses_custom_threshold_from_metadata(self):
        state = {
            "guardrail_result": GuardrailScoring(
                score=60, reasoning="Query is somewhat relevant", is_in_scope=True
            ),
            "metadata": {"guardrail_threshold": 50},
        }
        assert continue_after_guardrail(state) == "continue"


class TestContinueAfterGrading:
    """Tests for continue_after_grading edge function (legacy)."""

    def test_returns_routing_decision_when_present(self):
        state = {"routing_decision": "rewrite"}
        assert continue_after_grading(state) == "rewrite"

    def test_returns_generate_when_routing_decision_missing(self):
        state = {"routing_decision": None}
        assert continue_after_grading(state) == "generate"


class TestRouteAfterRouter:
    """Tests for route_after_router edge function."""

    def test_routes_to_execute_when_action_is_execute_tools_with_tool_calls(self):
        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[ToolCall(tool_name=RETRIEVE_CHUNKS, tool_args_json="{}")],
                reasoning="Need to retrieve relevant chunks",
            ),
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_router(state) == "execute"

    def test_routes_to_grade_when_generate_with_ungraded_chunks(self):
        state = {
            "router_decision": RouterDecision(
                action="generate",
                tool_calls=[],
                reasoning="Ready to generate response",
            ),
            "retrieved_chunks": [{"chunk_id": "1", "content": "Some content"}],
            "relevant_chunks": [],
        }
        assert route_after_router(state) == "grade"

    def test_routes_to_generate_when_generate_with_relevant_chunks(self):
        state = {
            "router_decision": RouterDecision(
                action="generate",
                tool_calls=[],
                reasoning="Ready to generate response",
            ),
            "retrieved_chunks": [{"chunk_id": "1", "content": "Some content"}],
            "relevant_chunks": [{"chunk_id": "1", "content": "Some content"}],
        }
        assert route_after_router(state) == "generate"

    def test_routes_to_generate_when_generate_with_no_retrieved_chunks(self):
        state = {
            "router_decision": RouterDecision(
                action="generate",
                tool_calls=[],
                reasoning="Generate response without context",
            ),
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_router(state) == "generate"

    def test_routes_to_generate_when_router_decision_missing(self):
        state = {
            "router_decision": None,
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_router(state) == "generate"


class TestRouteAfterGradingNew:
    """Tests for route_after_grading_new edge function."""

    def test_routes_to_generate_when_enough_relevant_chunks(self):
        state = {
            "relevant_chunks": [
                {"chunk_id": "1"},
                {"chunk_id": "2"},
                {"chunk_id": "3"},
            ],
            "metadata": {"top_k": 3},
            "max_iterations": 5,
            "iteration": 1,
        }
        assert route_after_grading_new(state) == "generate"

    def test_routes_to_router_when_insufficient_chunks_under_max_iterations(self):
        state = {
            "relevant_chunks": [{"chunk_id": "1"}],
            "metadata": {"top_k": 3},
            "max_iterations": 5,
            "iteration": 2,
        }
        assert route_after_grading_new(state) == "router"

    def test_routes_to_generate_when_max_iterations_reached(self):
        state = {
            "relevant_chunks": [{"chunk_id": "1"}],
            "metadata": {"top_k": 3},
            "max_iterations": 5,
            "iteration": 5,
        }
        assert route_after_grading_new(state) == "generate"

    def test_routes_to_router_when_empty_chunks_under_max_iterations(self):
        state = {
            "relevant_chunks": [],
            "metadata": {"top_k": 3},
            "max_iterations": 5,
            "iteration": 0,
        }
        assert route_after_grading_new(state) == "router"
