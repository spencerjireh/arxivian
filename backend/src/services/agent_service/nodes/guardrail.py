"""Guardrail node for query validation."""

from src.schemas.langgraph_state import AgentState, GuardrailScoring
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_context_aware_guardrail_prompt
from ..security import scan_for_injection

log = get_logger(__name__)


async def guardrail_node(state: AgentState, context: AgentContext) -> AgentState:
    """Validate query relevance with conversation context awareness."""
    query = state["messages"][-1].content
    query_str = query if isinstance(query, str) else str(query)
    state["original_query"] = query_str
    history = state.get("conversation_history", [])

    # Layer 1: Fast pattern scan
    scan_result = scan_for_injection(query_str)
    if scan_result.is_suspicious:
        log.warning(
            "injection_pattern_detected",
            patterns=scan_result.matched_patterns,
            query=query_str[:100],
        )

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

    state["guardrail_result"] = result
    state["metadata"]["guardrail_score"] = result.score
    state["metadata"]["injection_scan"] = {
        "suspicious": scan_result.is_suspicious,
        "patterns": list(scan_result.matched_patterns),
    }

    is_in_scope = result.score >= context.guardrail_threshold
    log.info(
        "guardrail_result",
        score=result.score,
        threshold=context.guardrail_threshold,
        in_scope=is_in_scope,
        suspicious=scan_result.is_suspicious,
        reasoning=result.reasoning[:100],
    )

    state["metadata"]["reasoning_steps"].append(
        f"Validated query scope (score: {result.score}/100)"
    )

    return state
