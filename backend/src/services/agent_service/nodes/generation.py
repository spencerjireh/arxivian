"""Answer generation node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import PromptBuilder, ANSWER_SYSTEM_PROMPT

log = get_logger(__name__)


async def generate_answer_node(state: AgentState, context: AgentContext) -> AgentState:
    """Generate final answer from relevant chunks with conversation context."""
    query = state.get("original_query") or ""
    chunks = state["relevant_chunks"][: context.top_k]
    history = state.get("conversation_history", [])
    attempts = state.get("retrieval_attempts", 1)

    log.debug(
        "generating answer",
        query=query[:100],
        chunks=len(chunks),
        history_len=len(history),
        attempts=attempts,
    )

    builder = (
        PromptBuilder(ANSWER_SYSTEM_PROMPT)
        .with_conversation(context.conversation_formatter, history)
        .with_retrieval_context(chunks)
        .with_query(query)
    )

    # Add note if limited sources found after max attempts
    if attempts >= context.max_retrieval_attempts and len(chunks) < context.top_k:
        builder.with_note("Limited sources found. Acknowledge gaps if needed.")

    system, user = builder.build()

    log.debug("llm prompt", system_len=len(system), user_len=len(user))

    answer = await context.llm_client.generate_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=context.temperature,
        max_tokens=1000,
        stream=False,
    )

    log.info("answer generated", answer_len=len(str(answer)), chunks_used=len(chunks))

    state["messages"].append(AIMessage(content=answer))
    state["metadata"]["reasoning_steps"].append("Generated answer with conversation context")

    return state
