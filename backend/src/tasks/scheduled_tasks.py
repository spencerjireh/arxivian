"""Scheduled background tasks."""

from typing import Any

from src.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.repositories.user_repository import UserRepository
from src.tasks.ingest_tasks import ingest_papers_task
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


@celery_app.task(name="src.tasks.scheduled_tasks.daily_ingest_task")
def daily_ingest_task() -> dict[str, Any]:
    """Run daily ingestion for all user-defined arXiv searches.

    Iterates through all users with saved arXiv searches in their
    preferences and queues an ingest task for each enabled search.

    Returns:
        Dictionary with summary of queued tasks
    """
    log.info("daily_ingest_started")

    async def _run() -> dict[str, Any]:
        queued_tasks = []
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_users_with_searches()

            for user in users:
                preferences = user.preferences or {}
                arxiv_searches = preferences.get("arxiv_searches", [])

                for search in arxiv_searches:
                    if not search.get("enabled", True):
                        continue

                    query = search.get("query")
                    if not query:
                        continue

                    # Queue ingestion task
                    task = ingest_papers_task.delay(
                        query=query,
                        categories=search.get("categories"),
                        max_results=search.get("max_results", 10),
                    )

                    queued_tasks.append({
                        "task_id": task.id,
                        "user_id": str(user.id),
                        "search_name": search.get("name", "Unnamed"),
                        "query": query,
                    })

                    log.info(
                        "ingest_task_queued",
                        task_id=task.id,
                        user_id=str(user.id),
                        query=query,
                    )

        return {
            "status": "completed",
            "tasks_queued": len(queued_tasks),
            "tasks": queued_tasks,
        }

    result = run_async(_run())
    log.info("daily_ingest_completed", tasks_queued=result["tasks_queued"])
    return result
