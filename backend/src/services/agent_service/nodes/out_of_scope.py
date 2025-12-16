"""Out of scope handler node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext
from ..prompts import PromptBuilder, OUT_OF_SCOPE_SYSTEM_PROMPT


async def out_of_scope_node(state: AgentState, context: AgentContext) -> AgentState:
    """Handle out-of-scope queries with LLM-generated response."""
    guardrail_result = state.get("guardrail_result")
    original_query = state.get("original_query") or ""
    history = state.get("conversation_history", [])

    if guardrail_result:
        system, user = (
            PromptBuilder(OUT_OF_SCOPE_SYSTEM_PROMPT)
            .with_conversation(context.conversation_formatter, history)
            .with_query(original_query, label="User query")
            .with_note(f"Score: {guardrail_result.score}/100. Reason: {guardrail_result.reasoning}")
            .build()
        )
        message = await context.llm_client.generate_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=False,
        )
    else:
        message = "I specialize in AI/ML research papers. How can I help with that?"

    state["messages"].append(AIMessage(content=message))
    return state
