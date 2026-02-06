"""API routes for background task operations."""

from celery.result import AsyncResult
from fastapi import APIRouter

from src.celery_app import celery_app
from src.dependencies import CurrentUserRequired
from src.schemas.ingest import IngestRequest
from src.schemas.tasks import AsyncTaskResponse, TaskStatusResponse
from src.tasks.ingest_tasks import ingest_papers_task
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/ingest/async", response_model=AsyncTaskResponse)
async def ingest_papers_async(
    request: IngestRequest,
    current_user: CurrentUserRequired,
) -> AsyncTaskResponse:
    """Queue paper ingestion as a background task.

    This endpoint queues the ingestion job and returns immediately with a task ID.
    Use GET /tasks/{task_id} to poll for completion status.

    The task will retry up to 3 times with exponential backoff on failure.
    """
    log.info(
        "async_ingest_requested",
        user_id=str(current_user.id),
        query=request.query,
        max_results=request.max_results,
    )

    task = ingest_papers_task.delay(
        query=request.query,
        max_results=request.max_results,
        categories=request.categories,
        start_date=request.start_date,
        end_date=request.end_date,
        force_reprocess=request.force_reprocess,
    )

    log.info("ingest_task_queued", task_id=task.id, user_id=str(current_user.id))

    return AsyncTaskResponse(task_id=task.id, status="queued")


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    include_result: bool = False,
) -> TaskStatusResponse:
    """Get the status of a background task.

    Args:
        task_id: The task ID returned from the async endpoint
        include_result: If true, include the task result on success (may be large)

    Returns:
        Task status including completion state
    """
    result = AsyncResult(task_id, app=celery_app)

    # Map Celery states to our API states
    status_map = {
        "PENDING": "pending",
        "STARTED": "started",
        "SUCCESS": "success",
        "FAILURE": "failure",
        "RETRY": "retry",
    }

    status = status_map.get(result.status, "pending")

    response = TaskStatusResponse(
        task_id=task_id,
        status=status,
        ready=result.ready(),
        result=None,
        error=None,
    )

    # Include result on success if requested
    if include_result and result.ready() and result.successful():
        try:
            response.result = result.result
        except Exception:
            pass

    # Include error on failure
    if result.failed():
        try:
            response.error = str(result.result)
        except Exception:
            response.error = "Unknown error"

    return response


@router.delete("/{task_id}")
async def revoke_task(
    task_id: str,
    current_user: CurrentUserRequired,
    terminate: bool = False,
) -> dict:
    """Revoke a pending or running task.

    Args:
        task_id: The task ID to revoke
        terminate: If true, terminate the task even if already running

    Note: Terminated tasks may leave partial results.
    """
    log.info(
        "task_revoke_requested",
        task_id=task_id,
        user_id=str(current_user.id),
        terminate=terminate,
    )

    celery_app.control.revoke(task_id, terminate=terminate)

    return {"task_id": task_id, "revoked": True, "terminated": terminate}
