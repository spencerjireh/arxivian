"""Ops operations router."""

from uuid import UUID

from fastapi import APIRouter

from src.celery_app import celery_app
from src.dependencies import (
    ApiKeyCheck,
    ChunkRepoDep,
    PaperRepoDep,
    UserRepoDep,
)
from src.exceptions import ForbiddenError, ResourceNotFoundError
from src.schemas.ops import (
    BulkIngestRequest,
    BulkIngestResponse,
    CleanupResponse,
    DeletePaperResponse,
    OrphanedPaper,
    RevokeTaskResponse,
    SystemSearchesResponse,
    UpdateSystemSearchesRequest,
    UpdateTierRequest,
    UpdateTierResponse,
)
from src.tasks.ingest_tasks import ingest_papers_task
from src.tiers import SYSTEM_USER_CLERK_ID, UserTier
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/ops", tags=["Ops"])


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
    _api_key: ApiKeyCheck,
) -> BulkIngestResponse:
    """Queue bulk ingestion of papers via arXiv IDs and/or search query."""
    task_ids: list[str] = []

    # Queue task for specific arXiv IDs
    if request.arxiv_ids:
        query = " OR ".join(f"id:{aid}" for aid in request.arxiv_ids)
        task = ingest_papers_task.delay(
            query=query,
            max_results=len(request.arxiv_ids),
            force_reprocess=request.force_reprocess,
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
        task_ids.append(task.id)

    log.info("bulk_ingest_queued", tasks_queued=len(task_ids), task_ids=task_ids)

    return BulkIngestResponse(tasks_queued=len(task_ids), task_ids=task_ids)


@router.delete("/tasks/{task_id}", response_model=RevokeTaskResponse)
async def revoke_task(
    task_id: str,
    _api_key: ApiKeyCheck,
    terminate: bool = False,
) -> RevokeTaskResponse:
    """Revoke a pending or running task by Celery id.

    Takes no existence check: `task_executions` was dropped in ARX-74, and it never held a
    row for a scheduled task anyway, so gating on it would have 404'd exactly the stuck
    weekly jobs this endpoint exists to kill. Celery ignores an unknown id.
    """
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
