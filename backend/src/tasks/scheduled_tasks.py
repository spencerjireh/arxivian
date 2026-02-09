"""Scheduled background tasks."""

import hashlib
from datetime import datetime, timezone
from typing import Any

from src.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.repositories.user_repository import UserRepository
from src.tasks.ingest_tasks import ingest_papers_task
from src.tasks.utils import run_async
from src.tiers import SYSTEM_USER_CLERK_ID
from src.utils.logger import get_logger

log = get_logger(__name__)

STAGGER_SECONDS = 30


def _deterministic_task_id(user_id: str, query: str) -> str:
    """Generate a deterministic task ID from date, user, and query."""
    key = f"{datetime.now(timezone.utc).date().isoformat()}:{user_id}:{query}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


@celery_app.task(name="src.tasks.scheduled_tasks.daily_ingest_task")
def daily_ingest_task() -> dict[str, Any]:
    """Run daily ingestion for system user arXiv searches.

    Reads arXiv search configs from the system user's preferences
    and queues an ingest task for each enabled search.
    Tasks are staggered with countdown to avoid thundering herd.

    Returns:
        Dictionary with summary of queued tasks
    """
    log.info("daily_ingest_started")

    async def _run() -> dict[str, Any]:
        queued_tasks = []
        task_index = 0
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            system_user = await user_repo.get_by_clerk_id(SYSTEM_USER_CLERK_ID)

            if system_user is None:
                log.warning("system_user_not_found")
                return {
                    "status": "completed",
                    "tasks_queued": 0,
                    "tasks": [],
                    "spread_duration_minutes": 0,
                }

            preferences = system_user.preferences or {}
            arxiv_searches = preferences.get("arxiv_searches", [])

            for search in arxiv_searches:
                if not search.get("enabled", True):
                    continue

                query = search.get("query")
                if not query:
                    continue

                det_id = _deterministic_task_id(str(system_user.id), query)

                search_name = search.get("name", "Unnamed")

                # Queue ingestion task with staggered countdown
                task = ingest_papers_task.apply_async(
                    kwargs={
                        "query": query,
                        "categories": search.get("categories"),
                        "max_results": search.get("max_results", 10),
                    },
                    countdown=task_index * STAGGER_SECONDS,
                    task_id=det_id,
                )

                queued_tasks.append(
                    {
                        "task_id": task.id,
                        "user_id": str(system_user.id),
                        "search_name": search_name,
                        "query": query,
                    }
                )

                log.info(
                    "ingest_task_queued",
                    task_id=task.id,
                    user_id=str(system_user.id),
                    query=query,
                    countdown=task_index * STAGGER_SECONDS,
                )

                task_index += 1

        spread_duration_minutes = (task_index - 1) * STAGGER_SECONDS / 60 if task_index > 0 else 0

        return {
            "status": "completed",
            "tasks_queued": len(queued_tasks),
            "tasks": queued_tasks,
            "spread_duration_minutes": round(spread_duration_minutes, 1),
        }

    result = run_async(_run())
    log.info("daily_ingest_completed", tasks_queued=result["tasks_queued"])
    return result
