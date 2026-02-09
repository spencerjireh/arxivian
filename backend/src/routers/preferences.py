"""API routes for user preferences management."""

from fastapi import APIRouter

from src.dependencies import CurrentUserRequired, DbSession, UserRepoDep, TierPolicyDep
from src.exceptions import ConflictError, ForbiddenError
from src.schemas.preferences import (
    ArxivSearchConfig,
    UpdateArxivSearchesRequest,
    UserPreferences,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/preferences", tags=["Preferences"])


@router.get("", response_model=UserPreferences)
async def get_preferences(
    current_user: CurrentUserRequired,
) -> UserPreferences:
    """Get the current user's preferences."""
    preferences = current_user.preferences or {}

    return UserPreferences.from_raw(preferences)


@router.put("/arxiv-searches", response_model=UserPreferences)
async def update_arxiv_searches(
    request: UpdateArxivSearchesRequest,
    current_user: CurrentUserRequired,
    db: DbSession,
    user_repo: UserRepoDep,
    policy: TierPolicyDep,
) -> UserPreferences:
    """Update the user's saved arXiv searches. Enforces slot limits."""
    # Enforce search slot limit
    enabled_count = sum(1 for s in request.arxiv_searches if s.enabled)
    if enabled_count > policy.search_slots:
        raise ForbiddenError(
            f"Search slot limit reached ({enabled_count}/{policy.search_slots})"
        )

    log.info(
        "updating_arxiv_searches",
        user_id=str(current_user.id),
        search_count=len(request.arxiv_searches),
    )

    # Get current preferences and update arxiv_searches
    current_prefs = current_user.preferences or {}
    current_prefs["arxiv_searches"] = [search.model_dump() for search in request.arxiv_searches]

    # Update user preferences
    await user_repo.update_preferences(current_user, current_prefs)
    await db.commit()

    log.info(
        "arxiv_searches_updated",
        user_id=str(current_user.id),
        search_count=len(request.arxiv_searches),
    )

    return UserPreferences.from_raw(current_prefs)


@router.post("/arxiv-searches", response_model=UserPreferences)
async def add_arxiv_search(
    search: ArxivSearchConfig,
    current_user: CurrentUserRequired,
    db: DbSession,
    user_repo: UserRepoDep,
    policy: TierPolicyDep,
) -> UserPreferences:
    """Add a new arXiv search to the user's preferences."""
    # Get current preferences and check slot limit
    current_prefs = current_user.preferences or {}
    arxiv_searches = current_prefs.get("arxiv_searches", [])

    enabled_count = sum(1 for s in arxiv_searches if s.get("enabled", True))
    if search.enabled and enabled_count >= policy.search_slots:
        raise ForbiddenError(
            f"Search slot limit reached ({enabled_count}/{policy.search_slots})"
        )

    log.info(
        "adding_arxiv_search",
        user_id=str(current_user.id),
        search_name=search.name,
    )

    # Enforce unique names (case-insensitive)
    if any(s.get("name", "").lower() == search.name.lower() for s in arxiv_searches):
        raise ConflictError(f"A search with the name '{search.name}' already exists")

    arxiv_searches.append(search.model_dump())
    current_prefs["arxiv_searches"] = arxiv_searches

    # Update user preferences
    await user_repo.update_preferences(current_user, current_prefs)
    await db.commit()

    log.info(
        "arxiv_search_added",
        user_id=str(current_user.id),
        search_name=search.name,
    )

    return UserPreferences.from_raw(current_prefs)


@router.delete("/arxiv-searches/{search_name}", response_model=UserPreferences)
async def delete_arxiv_search(
    search_name: str,
    current_user: CurrentUserRequired,
    db: DbSession,
    user_repo: UserRepoDep,
) -> UserPreferences:
    """Delete an arXiv search by name from the user's preferences."""
    log.info(
        "deleting_arxiv_search",
        user_id=str(current_user.id),
        search_name=search_name,
    )

    # Get current preferences and remove the search
    current_prefs = current_user.preferences or {}
    arxiv_searches = current_prefs.get("arxiv_searches", [])
    arxiv_searches = [s for s in arxiv_searches if s.get("name") != search_name]
    current_prefs["arxiv_searches"] = arxiv_searches

    # Update user preferences
    await user_repo.update_preferences(current_user, current_prefs)
    await db.commit()

    log.info(
        "arxiv_search_deleted",
        user_id=str(current_user.id),
        search_name=search_name,
    )

    return UserPreferences.from_raw(current_prefs)
