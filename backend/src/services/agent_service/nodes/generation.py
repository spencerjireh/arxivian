"""Answer generation node."""

from langchain_core.messages import AIMessage
from src.schemas.langgraph_state import AgentState
from ..context import AgentContext
from ..prompts import get_answer_generation_prompts


async def generate_answer_node(state: AgentState, context: AgentContext) -> dict:
    """Generate final answer from relevant chunks."""
    query = state["original_query"]
    chunks = state["relevant_chunks"][: context.top_k]

    context_str = "\n\n".join(
        [
            f"[Source {i+1} - {c['arxiv_id']}]\n"
            f"Title: {c['title']}\n"
            f"Section: {c.get('section_name', 'N/A')}\n"
            f"Content: {c['chunk_text']}"
            for i, c in enumerate(chunks)
        ]
    )

    system_prompt, user_prompt = get_answer_generation_prompts(query, context_str)

    answer = await context.llm_client.generate_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=context.temperature,
        max_tokens=1000,
        stream=False,
    )

    state["messages"].append(AIMessage(content=answer))
    state["metadata"]["reasoning_steps"].append("Generated answer from context")

    return state
