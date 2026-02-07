"""API routes for background task operations."""

from celery.result import AsyncResult
from fastapi import APIRouter, Query

from src.celery_app import celery_app
from src.dependencies import CurrentUserRequired, TaskExecRepoDep, DbSession
from src.exceptions import ResourceNotFoundError
from src.schemas.ingest import IngestRequest
from src.schemas.tasks import (
    AsyncTaskResponse,
    RevokeTaskResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskListItem,
)
from src.tasks.ingest_tasks import ingest_papers_task
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

_STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "RETRY": "retry",
    "REVOKED": "revoked",
}


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    current_user: CurrentUserRequired,
    task_repo: TaskExecRepoDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TaskListResponse:
    """List background tasks for the current user."""
    tasks, total = await task_repo.list_by_user(current_user.id, limit=limit, offset=offset)

    return TaskListResponse(
        tasks=[TaskListItem.model_validate(t, from_attributes=True) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/ingest/async", response_model=AsyncTaskResponse)
async def ingest_papers_async(
    request: IngestRequest,
    current_user: CurrentUserRequired,
    task_repo: TaskExecRepoDep,
    db: DbSession,
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

    # Record task execution for ownership tracking
    await task_repo.create(
        celery_task_id=task.id,
        user_id=current_user.id,
        task_type="ingest",
        parameters={
            "query": request.query,
            "max_results": request.max_results,
            "categories": request.categories,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "force_reprocess": request.force_reprocess,
        },
    )
    await db.commit()

    log.info("ingest_task_queued", task_id=task.id, user_id=str(current_user.id))

    return AsyncTaskResponse(task_id=task.id, status="queued", task_type="ingest")


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: CurrentUserRequired,
    task_repo: TaskExecRepoDep,
    include_result: bool = False,
) -> TaskStatusResponse:
    """Get the status of a background task.

    Args:
        task_id: The task ID returned from the async endpoint
        include_result: If true, include the task result on success (may be large)

    Returns:
        Task status including completion state
    """
    # Ownership check
    task_exec = await task_repo.get_by_user_and_celery_task_id(current_user.id, task_id)
    if task_exec is None:
        raise ResourceNotFoundError("Task", task_id)

    result = AsyncResult(task_id, app=celery_app)

    # Merge Celery status with DB record
    status = _STATUS_MAP.get(result.status, task_exec.status)

    response = TaskStatusResponse(
        task_id=task_id,
        status=status,
        ready=result.ready(),
        result=None,
        error=task_exec.error_message,
        task_type=task_exec.task_type,
        created_at=task_exec.created_at,
    )

    # Include result on success if requested
    if include_result and result.ready() and result.successful():
        try:
            response.result = result.result
        except Exception:
            log.debug("failed_to_deserialize_task_result", task_id=task_id)

    # Include error on failure
    if result.failed():
        try:
            response.error = str(result.result)
        except Exception:
            log.debug("failed_to_deserialize_task_error", task_id=task_id)
            response.error = response.error or "Unknown error"

    return response


@router.delete("/{task_id}", response_model=RevokeTaskResponse)
async def revoke_task(
    task_id: str,
    current_user: CurrentUserRequired,
    task_repo: TaskExecRepoDep,
    terminate: bool = False,
) -> RevokeTaskResponse:
    """Revoke a pending or running task.

    Args:
        task_id: The task ID to revoke
        terminate: If true, terminate the task even if already running

    Note: Terminated tasks may leave partial results.
    """
    # Ownership check
    task_exec = await task_repo.get_by_user_and_celery_task_id(current_user.id, task_id)
    if task_exec is None:
        raise ResourceNotFoundError("Task", task_id)

    log.info(
        "task_revoke_requested",
        task_id=task_id,
        user_id=str(current_user.id),
        terminate=terminate,
    )

    celery_app.control.revoke(task_id, terminate=terminate)

    return RevokeTaskResponse(task_id=task_id, revoked=True, terminated=terminate)
