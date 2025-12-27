"""Router node for dynamic tool selection."""

from __future__ import annotations
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from src.schemas.langgraph_state import AgentState, RouterDecision
from src.utils.logger import get_logger
from ..prompts import get_router_prompt

if TYPE_CHECKING:
    from ..context import AgentContext

log = get_logger(__name__)


async def router_node(state: AgentState, context: AgentContext) -> dict:
    """
    Router node that decides the next action.

    Uses LLM to dynamically select which tool to call (or generate response)
    based on the query, conversation history, and previous tool results.

    Args:
        state: Current agent state
        context: Agent context with LLM client and tool registry

    Returns:
        Updated state with router_decision
    """
    # Extract query from messages
    query = state.get("original_query") or ""
    if not query:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                content = msg.content
                query = content if isinstance(content, str) else str(content)
                break

    # Get tool schemas for prompt
    tool_schemas = context.tool_registry.get_all_schemas()

    # Format tool history for context
    tool_history = state.get("tool_history", [])
    tool_history_dicts = [
        {
            "tool_name": t.tool_name,
            "success": t.success,
            "result_summary": t.result_summary,
        }
        for t in tool_history
    ]

    # Format conversation history
    conversation_context = ""
    if state.get("conversation_history"):
        conversation_context = context.conversation_formatter.format_for_prompt(
            state["conversation_history"]
        )

    # Build router prompt
    system_prompt, user_prompt = get_router_prompt(
        query=query,
        tool_schemas=tool_schemas,
        tool_history=tool_history_dicts if tool_history_dicts else None,
        conversation_context=conversation_context,
    )

    # Increment iteration
    iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", context.max_iterations)

    # Check max iterations
    if iteration > max_iterations:
        log.warning("router max iterations reached", iteration=iteration, max=max_iterations)
        # Force generate if we've hit max iterations
        decision = RouterDecision(
            action="generate",
            reasoning=f"Max iterations ({max_iterations}) reached, generating response.",
        )
    else:
        # Get LLM decision
        log.debug("router calling LLM", query=query[:100], iteration=iteration)

        decision = await context.llm_client.generate_structured(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=RouterDecision,
        )

    log.info(
        "router decision",
        action=decision.action,
        tool_count=len(decision.tool_calls),
        tools=[tc.tool_name for tc in decision.tool_calls],
        iteration=iteration,
        reasoning=decision.reasoning[:100],
    )

    # Add reasoning step to metadata
    reasoning_steps = state.get("metadata", {}).get("reasoning_steps", [])
    tools_str = ", ".join(tc.tool_name for tc in decision.tool_calls) if decision.tool_calls else ""
    reasoning_steps.append(f"Router decision (iteration {iteration}): {decision.action} {tools_str}".strip())

    return {
        "router_decision": decision,
        "iteration": iteration,
        "status": "running",
        "metadata": {
            **state.get("metadata", {}),
            "reasoning_steps": reasoning_steps,
        },
    }
