"""Feed router -- the ranked weekly digest as cards (FEED-DIGEST-1/2)."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Query

from src.dependencies import CurrentUserOptional, FeedServiceDep
from src.exceptions import InvalidParameterError
from src.schemas.feed import FeedResponse

router = APIRouter()


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    user: CurrentUserOptional,
    feed_service: FeedServiceDep,
    week: date | None = Query(None, description="Any date; snapped to the Monday of its week"),
    category: list[str] | None = Query(None, description="Keep papers in any of these categories"),
    min_score: int | None = Query(None, ge=0, le=100, description="Minimum composite"),
    include_dismissed: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> FeedResponse:
    """One page of ranked paper cards for a digest week (default: the newest built week).

    Public: an anonymous caller gets the global digest under the default weights with no
    lifecycle state and no compute-profile match.
    """
    if week is not None and week > datetime.now(UTC).date():
        raise InvalidParameterError("week", week.isoformat(), "week must not be in the future")
    return await feed_service.get_feed(
        user,
        week=week,
        categories=category,
        min_score=min_score,
        include_dismissed=include_dismissed,
        offset=offset,
        limit=limit,
    )
