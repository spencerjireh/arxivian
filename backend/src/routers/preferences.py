"""API routes for user preferences management."""

from fastapi import APIRouter, HTTPException

from src.dependencies import CurrentUserRequired, DbSession, UserRepoDep
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

    return UserPreferences(
        arxiv_searches=[
            ArxivSearchConfig(**search) for search in preferences.get("arxiv_searches", [])
        ],
        notification_settings=preferences.get("notification_settings", {}),
    )


@router.put("/arxiv-searches", response_model=UserPreferences)
async def update_arxiv_searches(
    request: UpdateArxivSearchesRequest,
    current_user: CurrentUserRequired,
    db: DbSession,
    user_repo: UserRepoDep,
) -> UserPreferences:
    """Update the user's saved arXiv searches.

    This replaces all existing arXiv searches with the provided list.
    Searches are used by the daily ingestion job to automatically
    fetch new papers matching the user's interests.
    """
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

    return UserPreferences(
        arxiv_searches=request.arxiv_searches,
        notification_settings=current_prefs.get("notification_settings", {}),
    )


@router.post("/arxiv-searches", response_model=UserPreferences)
async def add_arxiv_search(
    search: ArxivSearchConfig,
    current_user: CurrentUserRequired,
    db: DbSession,
    user_repo: UserRepoDep,
) -> UserPreferences:
    """Add a new arXiv search to the user's preferences."""
    log.info(
        "adding_arxiv_search",
        user_id=str(current_user.id),
        search_name=search.name,
    )

    # Get current preferences and add the new search
    current_prefs = current_user.preferences or {}
    arxiv_searches = current_prefs.get("arxiv_searches", [])

    # Enforce unique names (case-insensitive)
    if any(s.get("name", "").lower() == search.name.lower() for s in arxiv_searches):
        raise HTTPException(
            status_code=409,
            detail=f"A search with the name '{search.name}' already exists",
        )

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

    return UserPreferences(
        arxiv_searches=[ArxivSearchConfig(**s) for s in arxiv_searches],
        notification_settings=current_prefs.get("notification_settings", {}),
    )


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

    return UserPreferences(
        arxiv_searches=[ArxivSearchConfig(**s) for s in arxiv_searches],
        notification_settings=current_prefs.get("notification_settings", {}),
    )
