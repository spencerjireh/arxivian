"""Out of scope handler node."""

from langchain_core.messages import AIMessage
from langchain_core.callbacks import adispatch_custom_event

from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger, truncate
from ..context import AgentContext
from ..prompts import PromptBuilder

log = get_logger(__name__)

OUT_OF_SCOPE_ENHANCED_PROMPT = """You are an AI/ML research assistant.
The user's query is outside your scope. Generate a helpful response that:

1. Acknowledges their message naturally (don't be robotic)
2. References the conversation topic if relevant
3. Explains your focus on AI/ML research papers
4. Suggests a relevant angle if their query could relate to AI/ML

Keep response to 2-3 sentences. Be warm but direct."""


async def out_of_scope_node(state: AgentState, context: AgentContext) -> AgentState:
    """Handle out-of-scope queries with context-aware response."""
    guardrail_result = state.get("guardrail_result")
    original_query = state.get("original_query") or ""
    history = state.get("conversation_history", [])

    injection_scan = state.get("metadata", {}).get("injection_scan", {})
    was_suspicious = injection_scan.get("suspicious", False)

    score = guardrail_result.score if guardrail_result else None
    log.info(
        "out_of_scope_response",
        query=original_query[:100],
        guardrail_score=score,
        was_suspicious=was_suspicious,
    )

    if guardrail_result:
        system, user = (
            PromptBuilder(OUT_OF_SCOPE_ENHANCED_PROMPT)
            .with_conversation(context.conversation_formatter, history)
            .with_query(original_query, label="User message")
            .with_note(f"Relevance score: {guardrail_result.score}/100")
            .with_note(f"Reason: {guardrail_result.reasoning}")
            .build()
        )

        # Use stream=True and emit tokens via custom events
        response = await context.llm_client.generate_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        # Collect streamed tokens and emit as custom events
        if isinstance(response, str):
            message = response
            await adispatch_custom_event("token", response)
        else:
            tokens: list[str] = []
            async for token in response:
                tokens.append(token)
                await adispatch_custom_event("token", token)
            message = "".join(tokens)
    else:
        message = "I specialize in AI/ML research papers. How can I help with that?"
        await adispatch_custom_event("token", message)

    log.info(
        "out of scope response generated",
        message=truncate(message, 500),
        message_len=len(message),
    )

    state["messages"].append(AIMessage(content=message))
    return state
