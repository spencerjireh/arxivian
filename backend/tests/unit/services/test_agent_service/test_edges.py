"""Tests for edge routing functions."""

from src.schemas.langgraph_state import (
    ClassificationResult,
    BatchEvaluation,
    ToolCall,
    ToolExecution,
)
from src.services.agent_service.edges import (
    route_after_classify,
    route_after_executor,
    route_after_eval,
)
from src.services.agent_service.tools import RETRIEVE_CHUNKS, LIST_PAPERS, ARXIV_SEARCH


class TestRouteAfterClassify:
    """Tests for route_after_classify edge function."""

    def test_out_of_scope_when_intent_is_out_of_scope(self):
        state = {
            "classification_result": ClassificationResult(
                intent="out_of_scope",
                scope_score=90,
                reasoning="Not related to academic research",
            ),
            "metadata": {},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "out_of_scope"

    def test_out_of_scope_when_score_below_default_threshold(self):
        state = {
            "classification_result": ClassificationResult(
                intent="direct",
                scope_score=70,
                reasoning="Borderline relevance",
            ),
            "metadata": {},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "out_of_scope"

    def test_out_of_scope_when_result_is_none(self):
        state = {
            "classification_result": None,
            "metadata": {},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "out_of_scope"

    def test_execute_when_intent_is_execute_with_tool_calls(self):
        state = {
            "classification_result": ClassificationResult(
                intent="execute",
                tool_calls=[ToolCall(tool_name=RETRIEVE_CHUNKS, tool_args_json="{}")],
                scope_score=90,
                reasoning="Need to retrieve relevant chunks",
            ),
            "metadata": {},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "execute"

    def test_generate_when_intent_is_direct_and_no_ungraded_chunks(self):
        state = {
            "classification_result": ClassificationResult(
                intent="direct",
                scope_score=85,
                reasoning="Can answer directly from context",
            ),
            "metadata": {},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "generate"

    def test_evaluate_safety_net_when_direct_but_ungraded_chunks_exist(self):
        """Safety net: intent is 'direct' but retrieved_chunks exist and relevant_chunks is empty."""
        state = {
            "classification_result": ClassificationResult(
                intent="direct",
                scope_score=85,
                reasoning="Can answer directly",
            ),
            "metadata": {},
            "retrieved_chunks": [{"chunk_id": "1", "content": "Some content"}],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "evaluate"

    def test_uses_custom_threshold_from_metadata(self):
        state = {
            "classification_result": ClassificationResult(
                intent="direct",
                scope_score=60,
                reasoning="Somewhat relevant query",
            ),
            "metadata": {"guardrail_threshold": 50},
            "retrieved_chunks": [],
            "relevant_chunks": [],
        }
        assert route_after_classify(state) == "generate"


class TestRouteAfterExecutor:
    """Tests for route_after_executor edge function."""

    def test_evaluate_when_retrieve_chunks_in_current_batch_and_succeeded(self):
        state = {
            "last_executed_tools": [RETRIEVE_CHUNKS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "evaluate"

    def test_classify_when_retrieve_chunks_not_in_current_batch(self):
        state = {
            "last_executed_tools": [LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "classify"

    def test_classify_when_no_tools_executed(self):
        state = {"last_executed_tools": [], "tool_history": []}
        assert route_after_executor(state) == "classify"

    def test_classify_when_last_executed_tools_missing(self):
        state = {"tool_history": []}
        assert route_after_executor(state) == "classify"

    def test_classify_when_retrieve_chunks_failed(self):
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
        assert route_after_executor(state) == "classify"

    def test_evaluate_with_parallel_execution_including_retrieve_chunks(self):
        state = {
            "last_executed_tools": [RETRIEVE_CHUNKS, LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=RETRIEVE_CHUNKS, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "evaluate"

    def test_classify_with_other_tools_only(self):
        state = {
            "last_executed_tools": [ARXIV_SEARCH, LIST_PAPERS],
            "tool_history": [
                ToolExecution(tool_name=ARXIV_SEARCH, tool_args={}, success=True),
                ToolExecution(tool_name=LIST_PAPERS, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "classify"

    def test_confirm_when_pause_reason_set(self):
        """When pause_reason is set (e.g. by propose_ingest), route to confirm."""
        state = {
            "pause_reason": "propose_ingest_confirmation",
            "last_executed_tools": [ARXIV_SEARCH],
            "tool_history": [
                ToolExecution(tool_name=ARXIV_SEARCH, tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "confirm"


class TestRouteAfterEval:
    """Tests for route_after_eval edge function."""

    def test_generate_when_sufficient(self):
        state = {
            "evaluation_result": BatchEvaluation(
                sufficient=True,
                reasoning="Chunks adequately answer the query",
            ),
            "max_iterations": 5,
            "iteration": 1,
        }
        assert route_after_eval(state) == "generate"

    def test_generate_when_evaluation_result_is_none(self):
        state = {
            "evaluation_result": None,
            "max_iterations": 5,
            "iteration": 1,
        }
        assert route_after_eval(state) == "generate"

    def test_generate_when_max_iterations_reached(self):
        state = {
            "evaluation_result": BatchEvaluation(
                sufficient=False,
                reasoning="Chunks are incomplete",
                suggested_rewrite="Try a more specific query",
            ),
            "max_iterations": 5,
            "iteration": 5,
        }
        assert route_after_eval(state) == "generate"

    def test_classify_when_insufficient_and_iterations_remain(self):
        state = {
            "evaluation_result": BatchEvaluation(
                sufficient=False,
                reasoning="Need more context",
                suggested_rewrite="Refine the search terms",
            ),
            "max_iterations": 5,
            "iteration": 2,
        }
        assert route_after_eval(state) == "classify"
