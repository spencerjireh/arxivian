"""Stage 2 deep-scoring driver task.

Stage 1 triage (`triage_tasks.py`) enqueues one `score_paper_task` per survivor. This is a
thin stub for now: it logs receipt and returns, so the Stage 1 -> Stage 2 hand-off is real
and end-to-end testable. SPE-270 replaces the body with the scoring-graph invocation
(`fetch_and_extract` -> 4 dimension nodes -> `compose_and_persist`) -- no signature or
enqueue-contract change. See `docs/design/scoring-pipeline.md` -> "Stage 2 -- Deep Scoring".
"""

from typing import Any

from src.celery_app import celery_app
from src.utils.logger import get_logger

log = get_logger(__name__)


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
    """Deep-score a single paper (Stage 2). Stub until SPE-270 wires the scoring graph.

    Args:
        self: Celery task instance (bound).
        arxiv_id: arXiv ID of a Stage 1 survivor. Stage 2 ingests the full text itself, so
            no `paper_id` is passed (the paper row may not exist yet).

    Returns:
        Dictionary with the (stubbed) scoring result.
    """
    log.info("score_paper_received", task_id=self.request.id, arxiv_id=arxiv_id)
    return {"status": "stub", "arxiv_id": arxiv_id}
