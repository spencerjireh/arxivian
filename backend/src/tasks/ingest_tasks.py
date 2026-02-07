"""Background tasks for paper ingestion."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from src.celery_app import celery_app
from src.database import AsyncSessionLocal
from src.factories.service_factories import get_ingest_service
from src.schemas.ingest import IngestRequest
from src.tasks.utils import run_async
from src.tasks.tracing import trace_task
from src.utils.logger import get_logger

log = get_logger(__name__)


def _persist_report(user_id: str, search_name: str, query: str, result: dict) -> None:
    """Best-effort persistence of ingest result to user's daily report.

    Opens a separate DB session so failures here never affect the ingest task.
    """

    async def _run() -> None:
        from src.repositories.report_repository import ReportRepository

        async with AsyncSessionLocal() as session:
            repo = ReportRepository(session)
            report = await repo.get_or_create_daily_report(
                user_id=UUID(user_id),
                report_date=datetime.now(timezone.utc).date(),
            )
            await repo.append_ingest_result(
                report=report,
                search_name=search_name,
                query=query,
                result=result,
            )
            await session.commit()

    try:
        run_async(_run())
        log.debug("report_persisted", user_id=user_id, search_name=search_name)
    except Exception as exc:
        log.warning(
            "report_persist_failed",
            user_id=user_id,
            search_name=search_name,
            error=str(exc),
        )


@celery_app.task(
    bind=True,
    name="src.tasks.ingest_tasks.ingest_papers_task",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 min between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
    rate_limit="6/m",
)
def ingest_papers_task(
    self,
    query: str,
    max_results: int = 10,
    categories: Optional[list[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_reprocess: bool = False,
    user_id: Optional[str] = None,
    search_name: Optional[str] = None,
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
        user_id: Optional user ID for report persistence (from scheduled tasks)
        search_name: Optional search name for report persistence

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

            # Persist to user report if called from scheduled task
            if user_id and search_name:
                try:
                    _persist_report(user_id, search_name, query, result)
                except Exception:
                    pass  # _persist_report logs internally; never fail the task

            return result
        except Exception as exc:
            log.error(
                "ingest_task_failed",
                task_id=task_id,
                attempt=attempt,
                max_retries=self.max_retries,
                error=str(exc),
            )
            raise  # autoretry_for handles retry logic
