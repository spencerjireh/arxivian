"""Answer generation node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext
from ..prompts import PromptBuilder, ANSWER_SYSTEM_PROMPT


async def generate_answer_node(state: AgentState, context: AgentContext) -> AgentState:
    """Generate final answer from relevant chunks with conversation context."""
    query = state.get("original_query") or ""
    chunks = state["relevant_chunks"][: context.top_k]
    history = state.get("conversation_history", [])
    attempts = state.get("retrieval_attempts", 1)

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

    answer = await context.llm_client.generate_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=context.temperature,
        max_tokens=1000,
        stream=False,
    )

    state["messages"].append(AIMessage(content=answer))
    state["metadata"]["reasoning_steps"].append("Generated answer with conversation context")

    return state
