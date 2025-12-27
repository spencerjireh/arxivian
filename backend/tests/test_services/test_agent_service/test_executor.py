"""Tests for executor node."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.schemas.langgraph_state import RouterDecision, ToolCall
from src.services.agent_service.tools import ToolResult


class TestExecutorNode:
    """Tests for executor_node function."""

    @pytest.fixture
    def mock_tool_registry(self):
        registry = AsyncMock()
        return registry

    @pytest.fixture
    def mock_context(self, mock_tool_registry):
        ctx = Mock()
        ctx.tool_registry = mock_tool_registry
        return ctx

    @pytest.fixture
    def base_state(self):
        return {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[ToolCall(tool_name="web_search", tool_args_json='{"query": "test"}')],
                reasoning="Testing",
            ),
            "tool_history": [],
            "metadata": {},
        }

    @pytest.mark.asyncio
    @patch(
        "src.services.agent_service.nodes.executor.adispatch_custom_event", new_callable=AsyncMock
    )
    async def test_successful_execution_records_tool_history(
        self, mock_event, mock_context, base_state
    ):
        from src.services.agent_service.nodes.executor import executor_node

        mock_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"results": []}, tool_name="web_search"
        )

        result = await executor_node(base_state, mock_context)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].tool_name == "web_search"
        assert result["tool_history"][0].success is True
        assert result["last_executed_tools"] == ["web_search"]

    @pytest.mark.asyncio
    @patch(
        "src.services.agent_service.nodes.executor.adispatch_custom_event", new_callable=AsyncMock
    )
    async def test_failed_execution_records_error(self, mock_event, mock_context, base_state):
        from src.services.agent_service.nodes.executor import executor_node

        mock_context.tool_registry.execute.return_value = ToolResult(
            success=False, error="API error", tool_name="web_search"
        )

        result = await executor_node(base_state, mock_context)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].success is False
        assert result["tool_history"][0].error == "API error"
        assert result["last_executed_tools"] == ["web_search"]

    @pytest.mark.asyncio
    @patch(
        "src.services.agent_service.nodes.executor.adispatch_custom_event", new_callable=AsyncMock
    )
    async def test_exception_during_execution_records_failure(
        self, mock_event, mock_context, base_state
    ):
        from src.services.agent_service.nodes.executor import executor_node

        mock_context.tool_registry.execute.side_effect = RuntimeError("Connection timeout")

        result = await executor_node(base_state, mock_context)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].success is False
        assert "Connection timeout" in result["tool_history"][0].error
        assert result["last_executed_tools"] == ["web_search"]

    @pytest.mark.asyncio
    @patch(
        "src.services.agent_service.nodes.executor.adispatch_custom_event", new_callable=AsyncMock
    )
    async def test_parallel_execution_mixed_results(self, mock_event, mock_context):
        from src.services.agent_service.nodes.executor import executor_node

        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[
                    ToolCall(tool_name="web_search", tool_args_json="{}"),
                    ToolCall(tool_name="list_papers", tool_args_json="{}"),
                ],
                reasoning="Testing parallel",
            ),
            "tool_history": [],
            "metadata": {},
        }

        # First call succeeds, second raises exception
        mock_context.tool_registry.execute.side_effect = [
            ToolResult(success=True, data={}, tool_name="web_search"),
            RuntimeError("Database error"),
        ]

        result = await executor_node(state, mock_context)

        assert len(result["tool_history"]) == 2
        assert result["tool_history"][0].success is True
        assert result["tool_history"][1].success is False
        assert "Database error" in result["tool_history"][1].error
        assert set(result["last_executed_tools"]) == {"web_search", "list_papers"}

    @pytest.mark.asyncio
    async def test_returns_empty_without_valid_decision(self, mock_context):
        from src.services.agent_service.nodes.executor import executor_node

        state = {"router_decision": None, "tool_history": [], "metadata": {}}

        result = await executor_node(state, mock_context)

        assert result == {}
