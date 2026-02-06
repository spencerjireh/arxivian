"""Background tasks for paper ingestion."""

from typing import Any, Optional

from src.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.factories.service_factories import get_ingest_service
from src.schemas.ingest import IngestRequest
from src.tasks.utils import run_async
from src.tasks.tracing import trace_task
from src.utils.logger import get_logger

log = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="src.tasks.ingest_tasks.ingest_papers_task",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 min between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def ingest_papers_task(
    self,
    query: str,
    max_results: int = 10,
    categories: Optional[list[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Background task for paper ingestion.

    Retries: 3 attempts with exponential backoff (approx 60s, 120s, 240s)
    On final failure: task marked as FAILURE in result backend

    Args:
        self: Celery task instance (bound)
        query: arXiv search query
        max_results: Maximum number of papers to fetch
        categories: Optional list of arXiv categories to filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        force_reprocess: Whether to re-process existing papers

    Returns:
        Dictionary with ingestion results
    """
    task_id = self.request.id
    attempt = self.request.retries + 1

    log.info(
        "ingest_task_started",
        task_id=task_id,
        query=query,
        max_results=max_results,
        attempt=attempt,
    )

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = get_ingest_service(session)
            request = IngestRequest(
                query=query,
                max_results=max_results,
                categories=categories,
                start_date=start_date,
                end_date=end_date,
                force_reprocess=force_reprocess,
            )
            result = await service.ingest_papers(request)
            await session.commit()
            return result.model_dump()

    with trace_task(
        "ingest_papers",
        task_id,
        {
            "query": query,
            "max_results": max_results,
            "categories": categories,
            "attempt": attempt,
        },
    ) as trace:
        try:
            result = run_async(_run())
            log.info(
                "ingest_task_completed",
                task_id=task_id,
                papers_processed=result.get("papers_processed", 0),
                chunks_created=result.get("chunks_created", 0),
            )

            # Add result metadata to trace
            if trace:
                trace.update(
                    metadata={
                        "papers_processed": result.get("papers_processed", 0),
                        "chunks_created": result.get("chunks_created", 0),
                    }
                )

            return result
        except Exception as exc:
            log.error(
                "ingest_task_failed",
                task_id=task_id,
                attempt=attempt,
                max_retries=3,
                error=str(exc),
            )
            raise  # autoretry_for handles retry logic
