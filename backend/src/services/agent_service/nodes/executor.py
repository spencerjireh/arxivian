"""Executor node for running tools selected by the router."""

from __future__ import annotations
import asyncio
import json

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from src.schemas.langgraph_state import AgentState, ToolExecution, ToolCall, ToolOutput
from src.services.agent_service.tools import ToolResult
from src.utils.logger import get_logger
from ..context import AgentContext

log = get_logger(__name__)


_PAPER_SUMMARY_VERBS = {"arxiv_search": "Found", "ingest_papers": "Ingested"}


def _summarize_result(tool_name: str, result: ToolResult) -> str:
    """Create brief summary of tool result including actionable details for the router."""
    if result.success and result.data:
        if isinstance(result.data, list):
            return f"Retrieved {len(result.data)} items"
        if isinstance(result.data, dict):
            if tool_name in _PAPER_SUMMARY_VERBS:
                papers = result.data.get("papers", [])
                if papers:
                    ids = [p.get("arxiv_id") for p in papers if isinstance(p, dict)]
                    count = result.data.get("count", result.data.get("papers_processed", len(ids)))
                    id_list = ", ".join(str(i) for i in ids[:10] if i)
                    verb = _PAPER_SUMMARY_VERBS[tool_name]
                    return f"{verb} {count} papers: [{id_list}]"
            if "total_count" in result.data:
                return f"Found {result.data['total_count']} items"
        return str(result.data)[:200]
    if result.error:
        return f"Error: {result.error}"
    return ""


async def executor_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Executor node that runs tools selected by the router.

    Executes tools in parallel and records results in tool_history.
    Also stores retrieved chunks for later grading/generation and
    captures non-retrieve tool outputs for generation context.
    """
    context: AgentContext = config["configurable"]["context"]

    decision = state.get("router_decision")

    if not decision or not decision.tool_calls:
        log.warning("executor called without valid tool decision")
        return {}

    async def run_single_tool(tc: ToolCall) -> tuple[str, dict, ToolResult]:
        """Execute one tool and return (name, args, result)."""
        tool_args = {}
        if tc.tool_args_json:
            try:
                tool_args = json.loads(tc.tool_args_json)
            except json.JSONDecodeError as e:
                log.warning("failed to parse tool_args_json", raw=tc.tool_args_json[:100])
                # Return a failed result for unparseable args
                return (
                    tc.tool_name,
                    {},
                    ToolResult(
                        success=False,
                        error=f"Invalid tool arguments: {e}",
                        tool_name=tc.tool_name,
                    ),
                )

        log.info("executor running tool", tool_name=tc.tool_name, args=str(tool_args)[:200])

        await adispatch_custom_event(
            "tool_start",
            {"tool_name": tc.tool_name, "args": tool_args},
            config=config,
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
            config=config,
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
    tool_outputs: list[ToolOutput] = []
    metadata = dict(state.get("metadata", {}))

    for idx, item in enumerate(results):
        tc = decision.tool_calls[idx]

        if isinstance(item, BaseException):
            log.error(
                "tool execution exception", tool_name=tc.tool_name, error=str(item), exc_info=True
            )
            tool_history.append(
                ToolExecution(
                    tool_name=tc.tool_name,
                    tool_args={},
                    success=False,
                    error=str(item),
                )
            )
            tool_outputs.append({"tool_name": tc.tool_name, "data": {"error": str(item)}})
            last_executed_tools.append(tc.tool_name)
            continue

        tool_name, tool_args, result = item
        last_executed_tools.append(tool_name)

        # Record execution
        execution = ToolExecution(
            tool_name=tool_name,
            tool_args=tool_args,
            success=result.success,
            result_summary=_summarize_result(tool_name, result),
            error=result.error,
        )
        tool_history.append(execution)

        # Use tool's class variables to determine where to store results.
        # Three cases: success+data -> store output, failure -> surface error,
        # success+no-data -> intentionally ignored (nothing to capture).
        if result.success and result.data:
            tool = context.tool_registry.get(tool_name)
            if tool:
                if tool.extends_chunks:
                    if not isinstance(result.data, list):
                        raise TypeError(
                            f"Tool '{tool_name}' declares extends_chunks=True but returned "
                            f"{type(result.data).__name__}, expected list"
                        )
                    retrieved_chunks.extend(result.data)
                else:
                    output: ToolOutput = {"tool_name": tool_name, "data": result.data}
                    if result.prompt_text is not None:
                        output["prompt_text"] = result.prompt_text
                    tool_outputs.append(output)
        elif not result.success:
            tool_outputs.append({"tool_name": tool_name, "data": {"error": result.error}})

    updates: dict = {
        "tool_history": tool_history,
        "last_executed_tools": last_executed_tools,
        "metadata": metadata,
        "tool_outputs": [*state.get("tool_outputs", []), *tool_outputs],
    }

    if retrieved_chunks:
        updates["retrieved_chunks"] = retrieved_chunks
        updates["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1

    return updates
