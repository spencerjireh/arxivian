"""Classify-and-route node: merged guardrail + router in a single LLM call."""

import re

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from src.schemas.langgraph_state import AgentState, ClassificationResult
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_classify_and_route_prompt
from ..security import scan_for_injection

log = get_logger(__name__)

SHORT_FOLLOWUP = re.compile(
    r"^(yes|no|explain|tell me more|why|how|what about|go on|continue)[.!?\s]*$", re.I
)


async def classify_and_route_node(state: AgentState, config: RunnableConfig) -> dict:
    """Classify query scope and route to the next action in a single LLM call.

    Layers:
    1. Injection scan (always runs)
    2. Fast-path: short conversational follow-ups skip LLM
    3. Max-iterations check: force direct intent without LLM
    4. LLM classification + routing
    """
    context: AgentContext = config["configurable"]["context"]

    # Resolve query: rewritten > original > last human message
    query = state.get("rewritten_query") or state.get("original_query") or ""
    if not query:
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                content = msg.content
                query = content if isinstance(content, str) else str(content)
                break

    history = state.get("conversation_history", [])
    metadata = dict(state.get("metadata", {}))
    reasoning_steps = list(metadata.get("reasoning_steps", []))
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", context.max_iterations)
    is_rewrite = iteration > 0

    # ── Layer 1: Injection scan (always) ────────────────────────────
    scan_result = scan_for_injection(query)
    if scan_result.is_suspicious:
        log.warning(
            "injection_pattern_detected",
            patterns=scan_result.matched_patterns,
            query=query[:100],
        )

    # ── Layer 2: Fast-path for short follow-ups ─────────────────────
    last_score = metadata.get("last_guardrail_score")
    prior_in_scope = last_score is None or last_score >= context.guardrail_threshold
    if (
        history
        and SHORT_FOLLOWUP.match(query)
        and not scan_result.is_suspicious
        and prior_in_scope
        and not is_rewrite
    ):
        result = ClassificationResult(
            intent="direct",
            scope_score=100,
            reasoning="conversational follow-up",
        )
        reasoning_steps.append(f"Validated query scope (score: {result.scope_score}/100)")
        return {
            "classification_result": result,
            "original_query": query,
            "metadata": {
                **metadata,
                "guardrail_score": result.scope_score,
                "injection_scan": {"suspicious": False, "patterns": []},
                "reasoning_steps": reasoning_steps,
            },
        }

    # ── Layer 3: Max-iterations guard ───────────────────────────────
    new_iteration = iteration + 1
    if new_iteration > max_iterations:
        log.warning(
            "classify_and_route max iterations reached",
            iteration=new_iteration,
            max=max_iterations,
        )
        result = ClassificationResult(
            intent="direct",
            scope_score=metadata.get("guardrail_score", 100),
            reasoning=f"Max iterations ({max_iterations}) reached, generating response.",
        )
        reasoning_steps.append(
            f"Classification (iteration {new_iteration}): forced direct (max iterations)"
        )
        return {
            "classification_result": result,
            "iteration": new_iteration,
            "status": "running",
            "metadata": {**metadata, "reasoning_steps": reasoning_steps},
        }

    # ── Layer 4: LLM classification + routing ───────────────────────
    tool_schemas = context.tool_registry.get_all_schemas()
    tool_history = state.get("tool_history", [])
    tool_history_dicts = [
        {
            "tool_name": t.tool_name,
            "success": t.success,
            "result_summary": t.result_summary,
        }
        for t in tool_history
    ]

    topic_context = context.conversation_formatter.format_as_topic_context(history)
    conversation_context = ""
    if history:
        conversation_context = context.conversation_formatter.format_for_prompt(history)

    prior_scope_score = metadata.get("guardrail_score") if is_rewrite else None

    system, user = get_classify_and_route_prompt(
        query=query,
        tool_schemas=tool_schemas,
        topic_context=topic_context,
        is_suspicious=scan_result.is_suspicious,
        threshold=context.guardrail_threshold,
        tool_history=tool_history_dicts if tool_history_dicts else None,
        conversation_context=conversation_context,
        is_rewrite=is_rewrite,
        prior_scope_score=prior_scope_score,
    )

    log.debug(
        "classify_and_route calling LLM",
        query=query[:100],
        iteration=new_iteration,
        is_rewrite=is_rewrite,
    )

    result = await context.llm_client.generate_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=ClassificationResult,
    )

    # On rewrite iterations, carry forward the original scope score
    if is_rewrite and prior_scope_score is not None:
        result = ClassificationResult(
            intent=result.intent,
            tool_calls=result.tool_calls,
            scope_score=prior_scope_score,
            reasoning=result.reasoning,
        )

    # Post-LLM guard: prevent re-emitting one-shot tools that already succeeded.
    # Tools with extends_chunks flow through evaluate_batch, which has its own
    # stagnation detection -- exempt them from the dedup guard.
    if result.intent == "execute" and result.tool_calls and tool_history:
        succeeded = {t.tool_name for t in tool_history if t.success}
        blocked = {
            name for name in succeeded
            if not getattr(context.tool_registry.get(name), "extends_chunks", False)
        }
        novel = [tc for tc in result.tool_calls if tc.tool_name not in blocked]
        if not novel:
            log.info(
                "classify_and_route: all requested tools already succeeded, forcing direct",
                requested=[tc.tool_name for tc in result.tool_calls],
            )
            result = ClassificationResult(
                intent="direct",
                scope_score=result.scope_score,
                reasoning="All requested tools already succeeded. "
                "Generating response from existing results.",
            )
        elif len(novel) < len(result.tool_calls):
            log.info(
                "classify_and_route: stripped duplicate tool calls",
                kept=[tc.tool_name for tc in novel],
                stripped=[
                    tc.tool_name for tc in result.tool_calls if tc.tool_name in blocked
                ],
            )
            result = ClassificationResult(
                intent=result.intent,
                tool_calls=novel,
                scope_score=result.scope_score,
                reasoning=result.reasoning,
            )

    log.info(
        "classify_and_route result",
        intent=result.intent,
        scope_score=result.scope_score,
        tool_count=len(result.tool_calls),
        tools=[tc.tool_name for tc in result.tool_calls],
        iteration=new_iteration,
        reasoning=result.reasoning[:100],
    )

    tools_str = ", ".join(tc.tool_name for tc in result.tool_calls) if result.tool_calls else ""
    reasoning_steps.append(
        f"Classification (iteration {new_iteration}): "
        f"intent={result.intent} score={result.scope_score} {tools_str}".strip()
    )

    return {
        "classification_result": result,
        "original_query": state.get("original_query") or query,
        "iteration": new_iteration,
        "status": "running",
        "metadata": {
            **metadata,
            "guardrail_score": result.scope_score,
            "injection_scan": {
                "suspicious": scan_result.is_suspicious,
                "patterns": list(scan_result.matched_patterns),
            },
            "reasoning_steps": reasoning_steps,
        },
    }
