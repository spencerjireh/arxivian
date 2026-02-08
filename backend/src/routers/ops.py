"""Ops operations router."""

from uuid import UUID

from fastapi import APIRouter

from src.schemas.ops import (
    CleanupResponse,
    OrphanedPaper,
    UpdateTierRequest,
    UpdateTierResponse,
)
from src.schemas.preferences import UpdateArxivSearchesRequest, UserPreferences
from src.dependencies import PaperRepoDep, DbSession, ApiKeyCheck, UserRepoDep
from src.exceptions import ResourceNotFoundError
from src.tiers import SYSTEM_USER_CLERK_ID, UserTier
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/ops", tags=["Ops"])


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_orphaned_records(
    paper_repo: PaperRepoDep,
    db: DbSession,
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

    await db.commit()

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
    db: DbSession,
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
        from src.exceptions import ForbiddenError

        raise ForbiddenError("Cannot modify system user tier")

    from sqlalchemy import update as sa_update
    from src.models.user import User

    await db.execute(sa_update(User).where(User.id == user_id).values(tier=tier.value))
    await db.commit()
    await db.refresh(user)

    log.info("user_tier_updated", user_id=str(user_id), tier=tier.value)

    return UpdateTierResponse(
        user_id=user_id,
        tier=user.tier,
        email=user.email,
    )


@router.put("/system/arxiv-searches", response_model=UserPreferences)
async def update_system_searches(
    request: UpdateArxivSearchesRequest,
    db: DbSession,
    user_repo: UserRepoDep,
    _api_key: ApiKeyCheck,
) -> UserPreferences:
    """Replace all system user arXiv searches. Idempotent PUT."""
    system_user = await user_repo.get_by_clerk_id(SYSTEM_USER_CLERK_ID)
    if system_user is None:
        raise ResourceNotFoundError("User", "system")

    current_prefs = system_user.preferences or {}
    current_prefs["arxiv_searches"] = [s.model_dump() for s in request.arxiv_searches]

    await user_repo.update_preferences(system_user, current_prefs)
    await db.commit()

    log.info(
        "system_searches_updated",
        search_count=len(request.arxiv_searches),
    )

    return UserPreferences(
        arxiv_searches=request.arxiv_searches,
        notification_settings=current_prefs.get("notification_settings", {}),
    )
