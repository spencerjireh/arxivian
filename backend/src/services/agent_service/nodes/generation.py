"""Answer generation node."""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger, truncate
from ..context import AgentContext
from ..prompts import PromptBuilder, ANSWER_SYSTEM_PROMPT

log = get_logger(__name__)


async def generate_answer_node(state: AgentState, config: RunnableConfig) -> dict:
    """Generate final answer from relevant chunks with conversation context."""
    context: AgentContext = config["configurable"]["context"]

    query = state.get("original_query") or ""
    chunks = state["relevant_chunks"][: context.top_k]
    history = state.get("conversation_history", [])
    attempts = state.get("retrieval_attempts", 1)
    tool_outputs = state.get("tool_outputs", [])

    log.debug(
        "generating answer",
        query=query[:100],
        chunks=len(chunks),
        history_len=len(history),
        attempts=attempts,
        tool_outputs=len(tool_outputs),
    )

    # Build system prompt with retrieval context and tool outputs
    builder = (
        PromptBuilder(ANSWER_SYSTEM_PROMPT)
        .with_retrieval_context(chunks)
        .with_tool_outputs(tool_outputs)
        .with_query(query)
    )

    # Add note if limited sources found after max attempts
    if attempts >= context.max_retrieval_attempts and len(chunks) < context.top_k:
        builder.with_note("Limited sources found. Acknowledge gaps if needed.")

    system, user_prompt = builder.build()

    # Build structured message turns for conversation history
    messages: list[dict] = [{"role": "system", "content": system}]
    max_history = context.conversation_formatter.max_turns * 2
    for msg in history[-max_history:]:
        content = msg["content"][:500] + ("..." if len(msg["content"]) > 500 else "")
        messages.append({"role": msg["role"], "content": content})
    messages.append({"role": "user", "content": user_prompt})

    log.debug("llm prompt", system_len=len(system), user_len=len(user_prompt))

    # Stream tokens via LangGraph stream writer
    writer = get_stream_writer()
    tokens: list[str] = []
    async for token in context.llm_client.generate_stream(
        messages=messages,
        temperature=context.temperature,
        max_tokens=context.max_generation_tokens,
    ):
        tokens.append(token)
        writer({"type": "token", "token": token})
    answer = "".join(tokens)

    log.info(
        "answer generated",
        answer=truncate(answer, 3000),
        answer_len=len(answer),
        chunks_used=len(chunks),
    )

    metadata = dict(state.get("metadata", {}))
    reasoning_steps = list(metadata.get("reasoning_steps", []))
    reasoning_steps.append("Generated answer with conversation context")

    return {
        "messages": [AIMessage(content=answer)],
        "metadata": {**metadata, "reasoning_steps": reasoning_steps},
    }
