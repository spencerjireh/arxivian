"""Stage 2 deep-scoring driver task.

Stage 1 triage (`triage_tasks.py`) enqueues one `score_paper_task` per survivor. This runs
the scoring graph (`fetch_and_extract` -> 4 dimension nodes -> `compose_and_persist`) and
persists `paper_scores` + `score_evidence`. The graph is compiled once per worker; each task
builds a fresh `ScoringContext` on its own async DB session (the FastAPI lifespan does not run
in the Celery worker). Takes only `arxiv_id` -- Stage 2 ingests the full text itself.
"""

from functools import lru_cache
from typing import Any

from langgraph.graph.state import CompiledStateGraph

from src.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.factories.service_factories import get_scoring_context
from src.schemas.scoring_state import RUBRIC_VERSION
from src.services.scoring_service.scoring_graph_builder import build_scoring_graph
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _scoring_graph() -> CompiledStateGraph:
    """Compile the scoring graph once per worker process."""
    return build_scoring_graph()


async def _run(arxiv_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        context = get_scoring_context(session)
        initial_state = {"arxiv_id": arxiv_id, "rubric_version": RUBRIC_VERSION}
        final_state = await _scoring_graph().ainvoke(
            initial_state, {"configurable": {"context": context}}
        )
        await session.commit()

    def _scored(key: str) -> bool:
        return final_state.get(key) is not None

    return {
        "status": "scored",
        "arxiv_id": arxiv_id,
        "paper_id": final_state.get("paper_id"),
        "rubric_version": RUBRIC_VERSION,
        "dimensions_scored": {
            "method_clarity": _scored("method_clarity_result"),
            "resource_feasibility": _scored("resource_feasibility_result"),
            "data_availability": _scored("data_availability_result"),
            "demand": _scored("demand_result"),
        },
    }


@celery_app.task(
    bind=True,
    name="src.tasks.score_tasks.score_paper_task",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def score_paper_task(self, arxiv_id: str) -> dict[str, Any]:
    """Deep-score a single Stage 1 survivor and persist its scores + evidence.

    Args:
        self: Celery task instance (bound).
        arxiv_id: arXiv ID of a survivor. No `paper_id` -- the paper row may not exist yet;
            the graph's fetch_and_extract ingests the full text and creates it.

    Returns:
        Summary dict: which dimensions were scored (soft-failed ones are False). Raises
        (triggering Celery autoretry) only on hard failures such as no usable full text.
    """
    log.info("score_paper_received", task_id=self.request.id, arxiv_id=arxiv_id)
    result = run_async(_run(arxiv_id))
    log.info("score_paper_done", task_id=self.request.id, arxiv_id=arxiv_id, result=result)
    return result
