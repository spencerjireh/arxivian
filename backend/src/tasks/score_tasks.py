"""Stage 2 deep-scoring driver task.

Stage 1 triage (`triage_tasks.py`) enqueues one `score_paper_task` per survivor. This runs
the scoring graph (`fetch_and_extract` -> 4 dimension nodes -> `compose_and_persist`) and
persists `paper_scores` + `score_evidence`. The graph is compiled once per worker; each task
builds a fresh `ScoringContext` on its own async DB session (the FastAPI lifespan does not run
in the Celery worker). Takes only `arxiv_id` -- Stage 2 ingests the full text itself.

Retry policy (SPE-283 / SPE-292): no blanket autoretry. `ScoringError` (no usable full
text -- the way an arXiv 429 or PDF failure during ingest surfaces) and TypeSafe
connection errors autoretry with a long jittered backoff (120 s factor, 600 s cap) so a
rate-limit cannot snowball across the survivor fan-out. A TypeSafe 429 retries after the
server's `retry_after` (at least 60 s). Any other error fails the task.
"""

from datetime import date
from functools import lru_cache
from typing import Any
from uuid import UUID

import redis
from langgraph.graph.state import CompiledStateGraph

from src.celery_app import celery_app
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.exceptions import ScoringError, TypeSafeConnectionError, TypeSafeRateLimitError
from src.factories import get_scoring_context
from src.services.scoring_service.scoring_graph_builder import build_scoring_graph
from src.services.scoring_service.state import RUBRIC_VERSION
from src.tasks.runtime import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


def ondemand_lock_key(arxiv_id: str) -> str:
    """Redis key that dedupes on-demand scoring requests for one paper (SPE-276)."""
    return f"score:ondemand:{arxiv_id}"


def ondemand_budget_keys(user_id: UUID | str, day: date) -> tuple[str, str]:
    """Redis counters that bound on-demand scoring per UTC day (SPE-302): global, per user."""
    stamp = day.isoformat()
    return f"score:ondemand:day:{stamp}", f"score:ondemand:user:{user_id}:{stamp}"


def release_ondemand_lock(arxiv_id: str) -> None:
    """Best-effort release of the on-demand lock; the key's TTL is the backstop."""
    try:
        client = redis.Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        try:
            client.delete(ondemand_lock_key(arxiv_id))
        finally:
            client.close()
    except Exception as e:
        log.warning("ondemand_lock_release_failed", arxiv_id=arxiv_id, error=str(e))


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


# Minimum wait before retrying a TypeSafe rate limit when the server sends no Retry-After.
RATE_LIMIT_MIN_COUNTDOWN_SECONDS = 60


@celery_app.task(
    bind=True,
    name="src.tasks.score_tasks.score_paper_task",
    max_retries=3,
    autoretry_for=(ScoringError, TypeSafeConnectionError),
    retry_backoff=120,
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
        only on hard failures: no usable full text / TypeSafe connection errors (autoretry
        with long backoff), a TypeSafe rate limit (retry after `retry_after`), or a
        non-retryable TypeSafe API error (task fails).
    """
    log.info("score_paper_received", task_id=self.request.id, arxiv_id=arxiv_id)
    try:
        result = run_async(_run(arxiv_id))
    except TypeSafeRateLimitError as e:
        countdown = max(int(e.retry_after or 0), RATE_LIMIT_MIN_COUNTDOWN_SECONDS)
        log.warning(
            "score_paper_rate_limited",
            task_id=self.request.id,
            arxiv_id=arxiv_id,
            countdown=countdown,
            retries=self.request.retries,
        )
        # Keep the on-demand lock: the retry is the same task, polls must not enqueue another.
        raise self.retry(exc=e, countdown=countdown) from e
    except Exception:
        release_ondemand_lock(arxiv_id)
        raise
    release_ondemand_lock(arxiv_id)
    log.info("score_paper_done", task_id=self.request.id, arxiv_id=arxiv_id, result=result)
    return result
