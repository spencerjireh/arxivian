"""Out of scope handler node."""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger, truncate
from ..context import AgentContext
from ..prompts import PromptBuilder

log = get_logger(__name__)

OUT_OF_SCOPE_ENHANCED_PROMPT = """You are an academic research assistant.
The user's query is outside your scope. Generate a helpful response that:

1. Acknowledges their message naturally (don't be robotic)
2. References the conversation topic if relevant
3. Explains your focus on academic research papers from arXiv
4. Suggests a relevant angle if their query could relate to academic research

Keep response to 2-3 sentences. Be warm but direct."""


async def out_of_scope_node(state: AgentState, config: RunnableConfig) -> dict:
    """Handle out-of-scope queries with context-aware response."""
    context: AgentContext = config["configurable"]["context"]

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

        # Stream tokens via LangGraph stream writer
        writer = get_stream_writer()
        tokens: list[str] = []
        async for token in context.llm_client.generate_stream(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=300,
        ):
            tokens.append(token)
            writer({"type": "token", "token": token})
        message = "".join(tokens)
    else:
        writer = get_stream_writer()
        message = "I specialize in academic research papers from arXiv. How can I help with that?"
        writer({"type": "token", "token": message})

    log.info(
        "out of scope response generated",
        message=truncate(message, 500),
        message_len=len(message),
    )

    return {"messages": [AIMessage(content=message)]}
