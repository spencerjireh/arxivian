"""Ops operations router."""

from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Query

from src.celery_app import celery_app
from src.schemas.ops import (
    BulkIngestRequest,
    BulkIngestResponse,
    CleanupResponse,
    OrphanedPaper,
    SystemSearchesResponse,
    UpdateSystemSearchesRequest,
    UpdateTierRequest,
    UpdateTierResponse,
)
from src.schemas.papers import DeletePaperResponse
from src.schemas.tasks import (
    RevokeTaskResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatusResponse,
)
from src.dependencies import (
    PaperRepoDep,
    ChunkRepoDep,
    ApiKeyCheck,
    UserRepoDep,
    TaskExecRepoDep,
)
from src.exceptions import ForbiddenError, ResourceNotFoundError
from src.tasks.ingest_tasks import ingest_papers_task
from src.tiers import SYSTEM_USER_CLERK_ID, UserTier, get_system_user_id
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/ops", tags=["Ops"])

_STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "RETRY": "retry",
    "REVOKED": "revoked",
}


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_orphaned_records(
    paper_repo: PaperRepoDep,
    _api_key: ApiKeyCheck,
) -> CleanupResponse:
    """Clean up orphaned database records (processed papers with no chunks)."""
    log.info("starting orphaned record cleanup")

    orphaned = await paper_repo.get_orphaned_papers()

    deleted_papers = []
    for paper in orphaned:
        arxiv_id = str(paper.arxiv_id)
        title = str(paper.title) if paper.title else ""
        deleted_papers.append(
            OrphanedPaper(
                arxiv_id=arxiv_id,
                title=title[:100],
                paper_id=str(paper.id),
            )
        )
        await paper_repo.delete(str(paper.id))
        log.debug("deleted orphaned paper", arxiv_id=arxiv_id)

    log.info(
        "orphaned record cleanup complete",
        found=len(orphaned),
        deleted=len(deleted_papers),
    )

    return CleanupResponse(
        orphaned_papers_found=len(orphaned),
        papers_deleted=len(deleted_papers),
        deleted_papers=deleted_papers,
    )


@router.patch("/users/{user_id}/tier", response_model=UpdateTierResponse)
async def update_user_tier(
    user_id: UUID,
    request: UpdateTierRequest,
    user_repo: UserRepoDep,
    _api_key: ApiKeyCheck,
) -> UpdateTierResponse:
    """Assign or change a user's tier. Protected by API key."""
    # Validate tier value (StrEnum raises ValueError on invalid)
    tier = UserTier(request.tier)

    user = await user_repo.get_by_id(str(user_id))
    if user is None:
        raise ResourceNotFoundError("User", str(user_id))

    # Prevent modifying system user
    if user.clerk_id == SYSTEM_USER_CLERK_ID:
        raise ForbiddenError("Cannot modify system user tier")

    user = await user_repo.update_tier(user, tier.value)

    log.info("user_tier_updated", user_id=str(user_id), tier=tier.value)

    return UpdateTierResponse(
        user_id=user_id,
        tier=user.tier,
        email=user.email,
    )


@router.get("/system/arxiv-searches", response_model=SystemSearchesResponse)
async def get_system_searches(
    user_repo: UserRepoDep,
    _api_key: ApiKeyCheck,
) -> SystemSearchesResponse:
    """Read current system user arXiv search configuration."""
    system_user = await user_repo.get_by_clerk_id(SYSTEM_USER_CLERK_ID)
    if system_user is None:
        raise ResourceNotFoundError("User", "system")

    prefs = system_user.preferences or {}

    return SystemSearchesResponse(arxiv_searches=prefs.get("arxiv_searches", []))


@router.put("/system/arxiv-searches", response_model=SystemSearchesResponse)
async def update_system_searches(
    request: UpdateSystemSearchesRequest,
    user_repo: UserRepoDep,
    _api_key: ApiKeyCheck,
) -> SystemSearchesResponse:
    """Replace all system user arXiv searches. Idempotent PUT."""
    system_user = await user_repo.get_by_clerk_id(SYSTEM_USER_CLERK_ID)
    if system_user is None:
        raise ResourceNotFoundError("User", "system")

    current_prefs = system_user.preferences or {}
    current_prefs["arxiv_searches"] = [s.model_dump() for s in request.arxiv_searches]

    await user_repo.update_preferences(system_user, current_prefs)

    log.info(
        "system_searches_updated",
        search_count=len(request.arxiv_searches),
    )

    return SystemSearchesResponse(arxiv_searches=request.arxiv_searches)


@router.post("/ingest", response_model=BulkIngestResponse)
async def bulk_ingest(
    request: BulkIngestRequest,
    task_repo: TaskExecRepoDep,
    _api_key: ApiKeyCheck,
) -> BulkIngestResponse:
    """Queue bulk ingestion of papers via arXiv IDs and/or search query."""
    system_user_id = get_system_user_id()
    task_ids: list[str] = []

    # Queue task for specific arXiv IDs
    if request.arxiv_ids:
        query = " OR ".join(f"id:{aid}" for aid in request.arxiv_ids)
        task = ingest_papers_task.delay(
            query=query,
            max_results=len(request.arxiv_ids),
            force_reprocess=request.force_reprocess,
        )
        await task_repo.create(
            celery_task_id=task.id,
            user_id=system_user_id,
            task_type="ingest",
            parameters={"arxiv_ids": request.arxiv_ids, "force_reprocess": request.force_reprocess},
        )
        task_ids.append(task.id)

    # Queue task for search query
    if request.search_query:
        task = ingest_papers_task.delay(
            query=request.search_query,
            max_results=request.max_results,
            categories=request.categories,
            force_reprocess=request.force_reprocess,
        )
        await task_repo.create(
            celery_task_id=task.id,
            user_id=system_user_id,
            task_type="ingest",
            parameters={
                "search_query": request.search_query,
                "max_results": request.max_results,
                "categories": request.categories,
                "force_reprocess": request.force_reprocess,
            },
        )
        task_ids.append(task.id)

    log.info("bulk_ingest_queued", tasks_queued=len(task_ids), task_ids=task_ids)

    return BulkIngestResponse(tasks_queued=len(task_ids), task_ids=task_ids)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    task_repo: TaskExecRepoDep,
    _api_key: ApiKeyCheck,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TaskListResponse:
    """List all task executions (no user filter)."""
    tasks, total = await task_repo.list_all(limit=limit, offset=offset)

    return TaskListResponse(
        tasks=[TaskListItem.model_validate(t, from_attributes=True) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    task_repo: TaskExecRepoDep,
    _api_key: ApiKeyCheck,
    include_result: bool = False,
) -> TaskStatusResponse:
    """Get task status by Celery task ID (no ownership check)."""
    task_exec = await task_repo.get_by_celery_task_id(task_id)
    if task_exec is None:
        raise ResourceNotFoundError("Task", task_id)

    result = AsyncResult(task_id, app=celery_app)
    status = _STATUS_MAP.get(result.status, task_exec.status)

    response = TaskStatusResponse(
        task_id=task_id,
        status=status,  # type: ignore[invalid-argument-type]  # dict.get returns str, not Literal
        ready=result.ready(),
        result=None,
        error=task_exec.error_message,
        task_type=task_exec.task_type,
        created_at=task_exec.created_at,
    )

    if include_result and result.ready() and result.successful():
        try:
            response.result = result.result
        except Exception:
            log.debug("failed_to_deserialize_task_result", task_id=task_id)

    if result.failed():
        try:
            response.error = str(result.result)
        except Exception:
            log.debug("failed_to_deserialize_task_error", task_id=task_id)
            response.error = response.error or "Unknown error"

    return response


@router.delete("/tasks/{task_id}", response_model=RevokeTaskResponse)
async def revoke_task(
    task_id: str,
    task_repo: TaskExecRepoDep,
    _api_key: ApiKeyCheck,
    terminate: bool = False,
) -> RevokeTaskResponse:
    """Revoke a pending or running task (no ownership check)."""
    task_exec = await task_repo.get_by_celery_task_id(task_id)
    if task_exec is None:
        raise ResourceNotFoundError("Task", task_id)

    log.info("task_revoke_requested", task_id=task_id, terminate=terminate)

    celery_app.control.revoke(task_id, terminate=terminate)

    return RevokeTaskResponse(task_id=task_id, revoked=True, terminated=terminate)


@router.delete("/papers/{arxiv_id}", response_model=DeletePaperResponse)
async def delete_paper(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    _api_key: ApiKeyCheck,
) -> DeletePaperResponse:
    """Delete a paper and its chunks. Protected by API key."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise ResourceNotFoundError("Paper", arxiv_id)

    chunk_count = await chunk_repo.count_by_paper_id(str(paper.id))
    title = paper.title

    await paper_repo.delete_by_arxiv_id(arxiv_id)

    return DeletePaperResponse(
        arxiv_id=arxiv_id,
        title=title,
        chunks_deleted=chunk_count,
    )
