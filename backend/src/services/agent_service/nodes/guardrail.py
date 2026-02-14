"""Guardrail node for query validation."""

import re

from langchain_core.runnables import RunnableConfig

from src.schemas.langgraph_state import AgentState, GuardrailScoring
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_context_aware_guardrail_prompt
from ..security import scan_for_injection

log = get_logger(__name__)

SHORT_FOLLOWUP = re.compile(
    r"^(yes|no|explain|tell me more|why|how|what about|go on|continue)[.!?\s]*$", re.I
)


async def guardrail_node(state: AgentState, config: RunnableConfig) -> dict:
    """Validate query relevance with conversation context awareness."""
    context: AgentContext = config["configurable"]["context"]

    query = state["messages"][-1].content
    query_str = query if isinstance(query, str) else str(query)
    history = state.get("conversation_history", [])
    metadata = dict(state.get("metadata", {}))
    reasoning_steps = list(metadata.get("reasoning_steps", []))

    # Layer 1: Fast pattern scan
    scan_result = scan_for_injection(query_str)
    if scan_result.is_suspicious:
        log.warning(
            "injection_pattern_detected",
            patterns=scan_result.matched_patterns,
            query=query_str[:100],
        )

    # Fast path: short conversational follow-ups skip LLM call,
    # but only if the prior turn was in scope.
    last_score = metadata.get("last_guardrail_score")
    prior_in_scope = last_score is None or last_score >= context.guardrail_threshold
    if (
        history
        and SHORT_FOLLOWUP.match(query_str)
        and not scan_result.is_suspicious
        and prior_in_scope
    ):
        result = GuardrailScoring(score=100, reasoning="conversational follow-up", is_in_scope=True)
        reasoning_steps.append(f"Validated query scope (score: {result.score}/100)")
        return {
            "guardrail_result": result,
            "original_query": query_str,
            "metadata": {
                **metadata,
                "guardrail_score": result.score,
                "injection_scan": {"suspicious": False, "patterns": []},
                "reasoning_steps": reasoning_steps,
            },
        }

    # Layer 2: Format topic context
    topic_context = context.conversation_formatter.format_as_topic_context(history)

    # Layer 3: Context-aware LLM evaluation
    system, user = get_context_aware_guardrail_prompt(
        query=query_str,
        topic_context=topic_context,
        threshold=context.guardrail_threshold,
        is_suspicious=scan_result.is_suspicious,
    )

    log.debug(
        "guardrail_check",
        query=query_str[:100],
        has_context=bool(topic_context),
        threshold=context.guardrail_threshold,
    )

    result = await context.llm_client.generate_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=GuardrailScoring,
    )

    is_in_scope = result.score >= context.guardrail_threshold
    log.info(
        "guardrail_result",
        score=result.score,
        threshold=context.guardrail_threshold,
        in_scope=is_in_scope,
        suspicious=scan_result.is_suspicious,
        reasoning=result.reasoning[:100],
    )

    reasoning_steps.append(f"Validated query scope (score: {result.score}/100)")

    return {
        "guardrail_result": result,
        "original_query": query_str,
        "metadata": {
            **metadata,
            "guardrail_score": result.score,
            "injection_scan": {
                "suspicious": scan_result.is_suspicious,
                "patterns": list(scan_result.matched_patterns),
            },
            "reasoning_steps": reasoning_steps,
        },
    }
