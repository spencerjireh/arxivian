"""Confirm ingest node -- HITL interrupt point for paper ingestion."""

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from src.schemas.langgraph_state import AgentState
from src.utils.logger import get_logger

log = get_logger(__name__)


async def confirm_ingest_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Suspend the graph until the user confirms or declines paper ingestion.

    Uses LangGraph's ``interrupt()`` to checkpoint state and wait. The service
    layer resumes with ``Command(resume=value)`` once the user responds.
    """
    pause_data = state.get("pause_data")

    log.info("confirm_ingest_node", papers=len(pause_data.get("papers", [])) if pause_data else 0)

    # Suspend execution -- returns the resume value when the graph is continued
    result = interrupt(pause_data)

    updates: dict = {"pause_reason": None, "pause_data": None}

    # Write result to tool_outputs so router/generation can reference it
    output_entry: dict = {"tool_name": "confirm_ingest", "data": result}
    if result.get("declined"):
        output_entry["prompt_text"] = "User declined paper ingestion."
        log.info("confirm_ingest declined")
    else:
        n = result.get("papers_processed", 0)
        output_entry["prompt_text"] = f"User approved. Ingested {n} papers."
        log.info("confirm_ingest approved", papers_processed=n)

    updates["tool_outputs"] = [*state.get("tool_outputs", []), output_entry]
    return updates
