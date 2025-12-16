"""Query rewrite node for improving retrieval."""

from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger
from ..context import AgentContext
from ..prompts import get_rewrite_prompt

log = get_logger(__name__)


async def rewrite_query_node(state: AgentState, context: AgentContext) -> AgentState:
    """Rewrite query based on grading feedback for better retrieval."""
    original_query = state.get("original_query") or ""
    grading_results = state["grading_results"]

    log.debug(
        "rewriting query", original=original_query[:100], grading_results=len(grading_results)
    )

    feedback = "\n".join(
        [
            f"- Chunk from {state['retrieved_chunks'][i]['arxiv_id']}: "
            f"{'RELEVANT' if g.is_relevant else 'NOT RELEVANT'} - {g.reasoning}"
            for i, g in enumerate(grading_results[:3])
        ]
    )

    prompt = get_rewrite_prompt(original_query, feedback)

    rewritten = await context.llm_client.generate_completion(
        messages=[{"role": "user", "content": prompt}], temperature=0.5
    )

    # Handle both str and AsyncIterator responses
    if isinstance(rewritten, str):
        rewritten_text = rewritten.strip()
    else:
        chunks = []
        async for chunk in rewritten:
            chunks.append(chunk)
        rewritten_text = "".join(chunks).strip()

    state["rewritten_query"] = rewritten_text

    log.info("query rewritten", original=original_query[:80], rewritten=rewritten_text[:80])

    state["metadata"]["reasoning_steps"].append(f"Rewrote query: '{rewritten_text}'")

    return state
