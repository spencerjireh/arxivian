"""Executor node for running tools selected by the router."""

from __future__ import annotations
import json
from typing import TYPE_CHECKING

from langgraph.types import Send
from langchain_core.callbacks.manager import adispatch_custom_event

from src.schemas.langgraph_state import AgentState, ToolExecution
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from ..context import AgentContext

log = get_logger(__name__)


async def executor_node(state: AgentState, context: AgentContext) -> dict:
    """
    Executor node that runs the tool selected by the router.

    Executes the tool and records the result in tool_history.
    Also stores retrieved chunks for later grading/generation.

    Args:
        state: Current agent state
        context: Agent context with tool registry

    Returns:
        Updated state with tool execution results
    """
    decision = state.get("router_decision")

    if not decision or decision.action != "execute_tool":
        log.warning("executor called without valid tool decision")
        return {}

    tool_name = decision.tool_name

    # Parse tool args from JSON string
    tool_args = {}
    if decision.tool_args_json:
        try:
            tool_args = json.loads(decision.tool_args_json)
        except json.JSONDecodeError:
            log.warning("failed to parse tool_args_json", raw=decision.tool_args_json[:100])

    log.info("executor running tool", tool_name=tool_name, args=str(tool_args)[:200])

    # Emit custom event for streaming
    await adispatch_custom_event(
        "tool_start",
        {"tool_name": tool_name, "args": tool_args},
    )

    # Execute the tool
    result = await context.tool_registry.execute(tool_name, **tool_args)

    log.info(
        "executor tool completed",
        tool_name=tool_name,
        success=result.success,
        error=result.error,
    )

    # Emit completion event
    await adispatch_custom_event(
        "tool_end",
        {"tool_name": tool_name, "success": result.success},
    )

    # Create execution record
    result_summary = ""
    if result.success and result.data:
        if isinstance(result.data, list):
            result_summary = f"Retrieved {len(result.data)} items"
        else:
            result_summary = str(result.data)[:100]
    elif result.error:
        result_summary = f"Error: {result.error}"

    execution = ToolExecution(
        tool_name=tool_name,
        tool_args=tool_args,
        success=result.success,
        result_summary=result_summary,
        error=result.error,
    )

    # Update tool history
    tool_history = list(state.get("tool_history", []))
    tool_history.append(execution)

    # Build return state
    updates: dict = {
        "tool_history": tool_history,
    }

    # Handle retrieve_chunks specifically - store for grading/generation
    if tool_name == "retrieve_chunks" and result.success and result.data:
        updates["retrieved_chunks"] = result.data
        # Increment retrieval attempts for compatibility with grading node
        updates["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1

    # Handle web_search - store results in metadata
    if tool_name == "web_search" and result.success and result.data:
        metadata = dict(state.get("metadata", {}))
        metadata["web_search_results"] = result.data
        updates["metadata"] = metadata

    return updates
