"""Guardrail node for query validation."""

from src.schemas.langgraph_state import AgentState, GuardrailScoring
from ..context import AgentContext
from ..prompts import get_guardrail_prompt


async def guardrail_node(state: AgentState, context: AgentContext) -> dict:
    """
    Validate query relevance to AI/ML research.

    Uses OpenAI structured outputs to score query on 0-100 scale.
    """
    query = state["messages"][-1].content
    state["original_query"] = query

    prompt = get_guardrail_prompt(query, context.guardrail_threshold)

    result = await context.llm_client.generate_structured(
        messages=[{"role": "user", "content": prompt}],
        response_format=GuardrailScoring,
    )

    state["guardrail_result"] = result
    state["metadata"]["guardrail_score"] = result.score
    state["metadata"]["reasoning_steps"].append(f"Validated query scope (score: {result.score}/100)")

    return state
