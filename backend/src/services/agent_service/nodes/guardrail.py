"""Guardrail node for query validation."""

from src.schemas.langgraph_state import AgentState, GuardrailScoring
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_guardrail_prompt

log = get_logger(__name__)


async def guardrail_node(state: AgentState, context: AgentContext) -> AgentState:
    """
    Validate query relevance to AI/ML research.

    Uses OpenAI structured outputs to score query on 0-100 scale.
    """
    query = state["messages"][-1].content
    query_str = query if isinstance(query, str) else str(query)
    state["original_query"] = query_str

    log.debug("guardrail check", query=query_str[:100], threshold=context.guardrail_threshold)

    prompt = get_guardrail_prompt(query_str, context.guardrail_threshold)

    result = await context.llm_client.generate_structured(
        messages=[{"role": "user", "content": prompt}],
        response_format=GuardrailScoring,
    )

    state["guardrail_result"] = result
    state["metadata"]["guardrail_score"] = result.score

    is_in_scope = result.score >= context.guardrail_threshold
    log.info(
        "guardrail result",
        score=result.score,
        threshold=context.guardrail_threshold,
        in_scope=is_in_scope,
        reasoning=result.reasoning[:100],
    )

    state["metadata"]["reasoning_steps"].append(
        f"Validated query scope (score: {result.score}/100)"
    )

    return state
