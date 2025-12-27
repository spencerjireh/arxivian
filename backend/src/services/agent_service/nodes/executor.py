"""Executor node for running tools selected by the router."""

from __future__ import annotations
import asyncio
import json
from typing import TYPE_CHECKING

from langchain_core.callbacks.manager import adispatch_custom_event

from src.schemas.langgraph_state import AgentState, ToolExecution, ToolCall
from src.services.agent_service.tools import ToolResult
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from ..context import AgentContext

log = get_logger(__name__)


def _summarize_result(result: ToolResult) -> str:
    """Create brief summary of tool result."""
    if result.success and result.data:
        if isinstance(result.data, list):
            return f"Retrieved {len(result.data)} items"
        if isinstance(result.data, dict) and "total_count" in result.data:
            return f"Found {result.data['total_count']} items"
        return str(result.data)[:100]
    if result.error:
        return f"Error: {result.error}"
    return ""


async def executor_node(state: AgentState, context: AgentContext) -> dict:
    """
    Executor node that runs tools selected by the router.

    Executes tools in parallel and records results in tool_history.
    Also stores retrieved chunks for later grading/generation.

    Args:
        state: Current agent state
        context: Agent context with tool registry

    Returns:
        Updated state with tool execution results
    """
    decision = state.get("router_decision")

    if not decision or decision.action != "execute_tools" or not decision.tool_calls:
        log.warning("executor called without valid tool decision")
        return {}

    async def run_single_tool(tc: ToolCall) -> tuple[str, dict, ToolResult]:
        """Execute one tool and return (name, args, result)."""
        tool_args = {}
        if tc.tool_args_json:
            try:
                tool_args = json.loads(tc.tool_args_json)
            except json.JSONDecodeError:
                log.warning("failed to parse tool_args_json", raw=tc.tool_args_json[:100])

        log.info("executor running tool", tool_name=tc.tool_name, args=str(tool_args)[:200])

        await adispatch_custom_event(
            "tool_start",
            {"tool_name": tc.tool_name, "args": tool_args},
        )

        result = await context.tool_registry.execute(tc.tool_name, **tool_args)

        log.info(
            "executor tool completed",
            tool_name=tc.tool_name,
            success=result.success,
            error=result.error,
        )

        await adispatch_custom_event(
            "tool_end",
            {"tool_name": tc.tool_name, "success": result.success},
        )

        return tc.tool_name, tool_args, result

    # Run all tools in parallel
    results = await asyncio.gather(
        *[run_single_tool(tc) for tc in decision.tool_calls],
        return_exceptions=True,
    )

    # Process results
    tool_history = list(state.get("tool_history", []))
    last_executed_tools: list[str] = []
    retrieved_chunks: list[dict] = []
    metadata = dict(state.get("metadata", {}))

    for idx, item in enumerate(results):
        tc = decision.tool_calls[idx]

        if isinstance(item, Exception):
            log.error("tool execution exception", tool_name=tc.tool_name, error=str(item))
            tool_history.append(
                ToolExecution(
                    tool_name=tc.tool_name,
                    tool_args={},
                    success=False,
                    error=str(item),
                )
            )
            last_executed_tools.append(tc.tool_name)
            continue

        tool_name, tool_args, result = item
        last_executed_tools.append(tool_name)

        # Record execution
        execution = ToolExecution(
            tool_name=tool_name,
            tool_args=tool_args,
            success=result.success,
            result_summary=_summarize_result(result),
            error=result.error,
        )
        tool_history.append(execution)

        # Merge tool-specific results
        if tool_name == "retrieve_chunks" and result.success and result.data:
            retrieved_chunks.extend(result.data)
        if tool_name == "web_search" and result.success and result.data:
            metadata["web_search_results"] = result.data
        if tool_name == "list_papers" and result.success and result.data:
            metadata["list_papers_results"] = result.data
        if tool_name == "ingest_papers" and result.success and result.data:
            metadata["ingest_papers_results"] = result.data

    updates: dict = {
        "tool_history": tool_history,
        "last_executed_tools": last_executed_tools,
        "metadata": metadata,
    }

    if retrieved_chunks:
        updates["retrieved_chunks"] = retrieved_chunks
        updates["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1

    return updates
