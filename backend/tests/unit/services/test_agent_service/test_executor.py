"""Tests for executor node."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.schemas.langgraph_state import RouterDecision, ToolCall
from src.services.agent_service.tools import ToolResult, LIST_PAPERS, ARXIV_SEARCH


class TestExecutorNode:
    """Tests for executor_node function."""

    @pytest.fixture
    def mock_tool_registry(self):
        registry = AsyncMock()
        return registry

    @pytest.fixture
    def mock_exec_context(self, mock_tool_registry):
        ctx = Mock()
        ctx.tool_registry = mock_tool_registry
        # Mock tool without extends_chunks (non-retrieve)
        mock_tool = Mock()
        mock_tool.extends_chunks = False
        mock_tool.sets_pause = False
        # Override get to return a regular Mock, not an async one
        ctx.tool_registry.get = Mock(return_value=mock_tool)
        return ctx

    @pytest.fixture
    def exec_config(self, mock_exec_context):
        return {"configurable": {"context": mock_exec_context}}

    @pytest.fixture
    def base_state(self):
        return {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[ToolCall(tool_name=LIST_PAPERS, tool_args_json='{"query": "test"}')],
                reasoning="Testing",
            ),
            "tool_history": [],
            "tool_outputs": [],
            "metadata": {},
        }

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_successful_execution_records_tool_history(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"total_count": 5, "papers": []}, tool_name=LIST_PAPERS
        )

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].tool_name == LIST_PAPERS
        assert result["tool_history"][0].success is True
        assert result["last_executed_tools"] == [LIST_PAPERS]

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_tool_outputs_captured_for_non_retrieve_tools(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        """Non-retrieve tool outputs are captured in tool_outputs for generation."""
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"total_count": 5, "papers": []}, tool_name=LIST_PAPERS
        )

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_outputs"]) == 1
        assert result["tool_outputs"][0]["tool_name"] == LIST_PAPERS
        assert result["tool_outputs"][0]["data"]["total_count"] == 5

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_prompt_text_propagated_from_tool_result(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        """prompt_text from ToolResult is propagated to tool output."""
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True,
            data={"total_count": 5, "papers": []},
            prompt_text="Formatted output text",
            tool_name=LIST_PAPERS,
        )

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_outputs"]) == 1
        assert result["tool_outputs"][0]["prompt_text"] == "Formatted output text"

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_prompt_text_absent_when_tool_result_has_none(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        """prompt_text is NOT added to tool output when ToolResult.prompt_text is None."""
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"total_count": 5, "papers": []}, tool_name=LIST_PAPERS
        )

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_outputs"]) == 1
        assert "prompt_text" not in result["tool_outputs"][0]

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_tool_outputs_accumulate_across_iterations(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        """Tool outputs from previous iterations are preserved, not deduplicated."""
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"total_count": 3, "papers": ["new"]}, tool_name=LIST_PAPERS
        )

        # Simulate prior iteration having already produced a list_papers output
        base_state["tool_outputs"] = [
            {"tool_name": LIST_PAPERS, "data": {"total_count": 5, "papers": ["old"]}}
        ]

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_outputs"]) == 2
        assert result["tool_outputs"][0]["data"]["total_count"] == 5
        assert result["tool_outputs"][1]["data"]["total_count"] == 3

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_failed_execution_records_error(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=False, error="API error", tool_name=LIST_PAPERS
        )

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].success is False
        assert result["tool_history"][0].error == "API error"
        assert result["last_executed_tools"] == [LIST_PAPERS]

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_exception_during_execution_records_failure(
        self, mock_get_writer, mock_exec_context, exec_config, base_state
    ):
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        mock_exec_context.tool_registry.execute.side_effect = RuntimeError("Connection timeout")

        result = await executor_node(base_state, exec_config)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].success is False
        assert "Connection timeout" in result["tool_history"][0].error
        assert result["last_executed_tools"] == [LIST_PAPERS]

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_parallel_execution_mixed_results(self, mock_get_writer, mock_exec_context):
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        exec_config = {"configurable": {"context": mock_exec_context}}
        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[
                    ToolCall(tool_name=ARXIV_SEARCH, tool_args_json="{}"),
                    ToolCall(tool_name=LIST_PAPERS, tool_args_json="{}"),
                ],
                reasoning="Testing parallel",
            ),
            "tool_history": [],
            "tool_outputs": [],
            "metadata": {},
        }

        # First call succeeds, second raises exception
        mock_exec_context.tool_registry.execute.side_effect = [
            ToolResult(success=True, data={}, tool_name=ARXIV_SEARCH),
            RuntimeError("Database error"),
        ]

        result = await executor_node(state, exec_config)

        assert len(result["tool_history"]) == 2
        assert result["tool_history"][0].success is True
        assert result["tool_history"][1].success is False
        assert "Database error" in result["tool_history"][1].error
        assert set(result["last_executed_tools"]) == {ARXIV_SEARCH, LIST_PAPERS}

    @pytest.mark.asyncio
    async def test_returns_empty_without_valid_decision(self, mock_exec_context):
        from src.services.agent_service.nodes.executor import executor_node

        exec_config = {"configurable": {"context": mock_exec_context}}
        state = {"router_decision": None, "tool_history": [], "tool_outputs": [], "metadata": {}}

        result = await executor_node(state, exec_config)

        assert result == {}

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_extends_chunks_with_non_list_raises_type_error(
        self, mock_get_writer, mock_exec_context
    ):
        """Tool declaring extends_chunks=True must return a list."""
        from src.services.agent_service.nodes.executor import executor_node
        from src.services.agent_service.tools import RETRIEVE_CHUNKS

        mock_get_writer.return_value = MagicMock()

        # Configure mock tool to declare extends_chunks=True
        mock_tool = Mock()
        mock_tool.extends_chunks = True
        mock_tool.sets_pause = False
        mock_exec_context.tool_registry.get = Mock(return_value=mock_tool)

        # Return a dict instead of a list
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data={"not": "a list"}, tool_name=RETRIEVE_CHUNKS
        )

        exec_config = {"configurable": {"context": mock_exec_context}}
        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[
                    ToolCall(tool_name=RETRIEVE_CHUNKS, tool_args_json='{"query": "test"}')
                ],
                reasoning="Testing",
            ),
            "tool_history": [],
            "tool_outputs": [],
            "metadata": {},
        }

        with pytest.raises(TypeError) as exc_info:
            await executor_node(state, exec_config)

        assert "extends_chunks=True" in str(exc_info.value)
        assert "dict" in str(exc_info.value)
        assert "expected list" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_extends_chunks_with_list_succeeds(self, mock_get_writer, mock_exec_context):
        """Tool declaring extends_chunks=True works correctly with list data."""
        from src.services.agent_service.nodes.executor import executor_node
        from src.services.agent_service.tools import RETRIEVE_CHUNKS

        mock_get_writer.return_value = MagicMock()

        mock_tool = Mock()
        mock_tool.extends_chunks = True
        mock_tool.sets_pause = False
        mock_exec_context.tool_registry.get = Mock(return_value=mock_tool)

        chunks = [{"chunk_id": "1", "text": "test"}]
        mock_exec_context.tool_registry.execute.return_value = ToolResult(
            success=True, data=chunks, tool_name=RETRIEVE_CHUNKS
        )

        exec_config = {"configurable": {"context": mock_exec_context}}
        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[
                    ToolCall(tool_name=RETRIEVE_CHUNKS, tool_args_json='{"query": "test"}')
                ],
                reasoning="Testing",
            ),
            "tool_history": [],
            "tool_outputs": [],
            "metadata": {},
        }

        result = await executor_node(state, exec_config)

        assert result["retrieved_chunks"] == chunks
        assert result["retrieval_attempts"] == 1

    @pytest.mark.asyncio
    @patch("src.services.agent_service.nodes.executor.get_stream_writer")
    async def test_json_parse_failure_records_error(self, mock_get_writer, mock_exec_context):
        """Invalid JSON in tool_args_json records a failed execution."""
        from src.services.agent_service.nodes.executor import executor_node

        mock_get_writer.return_value = MagicMock()
        exec_config = {"configurable": {"context": mock_exec_context}}
        state = {
            "router_decision": RouterDecision(
                action="execute_tools",
                tool_calls=[
                    ToolCall(tool_name=LIST_PAPERS, tool_args_json="not valid json")
                ],
                reasoning="Testing",
            ),
            "tool_history": [],
            "tool_outputs": [],
            "metadata": {},
        }

        result = await executor_node(state, exec_config)

        assert len(result["tool_history"]) == 1
        assert result["tool_history"][0].success is False
        assert "Invalid tool arguments" in result["tool_history"][0].error
