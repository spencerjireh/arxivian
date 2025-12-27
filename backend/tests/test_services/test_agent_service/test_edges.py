"""Tests for edge routing functions."""

import pytest

from src.schemas.langgraph_state import ToolExecution
from src.services.agent_service.edges import route_after_executor


class TestRouteAfterExecutor:
    """Tests for route_after_executor edge function."""

    def test_routes_to_grade_when_retrieve_chunks_in_current_batch(self):
        state = {
            "last_executed_tools": ["retrieve_chunks"],
            "tool_history": [
                ToolExecution(tool_name="retrieve_chunks", tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "grade"

    def test_routes_to_router_when_retrieve_chunks_in_history_but_not_current_batch(self):
        # Simulates: retrieve_chunks was called in iteration 1, web_search in iteration 2
        state = {
            "last_executed_tools": ["web_search"],
            "tool_history": [
                ToolExecution(tool_name="retrieve_chunks", tool_args={}, success=True),
                ToolExecution(tool_name="web_search", tool_args={}, success=True),
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
            "last_executed_tools": ["retrieve_chunks"],
            "tool_history": [
                ToolExecution(
                    tool_name="retrieve_chunks",
                    tool_args={},
                    success=False,
                    error="Connection failed",
                ),
            ],
        }
        assert route_after_executor(state) == "router"

    def test_routes_to_grade_with_parallel_execution_including_retrieve_chunks(self):
        # Both retrieve_chunks and web_search executed in parallel
        state = {
            "last_executed_tools": ["retrieve_chunks", "web_search"],
            "tool_history": [
                ToolExecution(tool_name="retrieve_chunks", tool_args={}, success=True),
                ToolExecution(tool_name="web_search", tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "grade"

    def test_routes_to_router_with_other_tools_only(self):
        state = {
            "last_executed_tools": ["web_search", "list_papers"],
            "tool_history": [
                ToolExecution(tool_name="web_search", tool_args={}, success=True),
                ToolExecution(tool_name="list_papers", tool_args={}, success=True),
            ],
        }
        assert route_after_executor(state) == "router"
