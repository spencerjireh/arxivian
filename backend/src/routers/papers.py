"""Papers management router."""

import re
import uuid
from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.schemas.papers import (
    PaperResponse,
    PaperListResponse,
    PaperListItem,
)
from src.schemas.feed import PaperScoreDetailResponse, ScorePendingResponse
from src.dependencies import (
    CurrentUserRequired,
    FeedServiceDep,
    PaperRepoDep,
    RedisDep,
    SettingsDep,
    TaskExecRepoDep,
)
from src.exceptions import InvalidParameterError, ResourceNotFoundError
from src.tasks.score_tasks import ondemand_lock_key, score_paper_task

router = APIRouter()

# New-style ids (2301.00001, 2301.00001v2). Old-style ids contain a slash and do not
# route through this path segment; they predate the feed and are not expected here.
_ARXIV_ID_RE = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?$")


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    paper_repo: PaperRepoDep,
    _user: CurrentUserRequired,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    processed_only: Optional[bool] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Literal["created_at", "published_date", "updated_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> PaperListResponse:
    """Get paginated list of papers from the communal knowledge base."""
    papers, total = await paper_repo.get_all(
        offset=offset,
        limit=limit,
        processed_only=processed_only,
        category_filter=category,
        author_filter=author,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    paper_items = [PaperListItem.model_validate(p, from_attributes=True) for p in papers]

    return PaperListResponse(total=total, offset=offset, limit=limit, papers=paper_items)


@router.get("/papers/{arxiv_id}", response_model=PaperResponse)
async def get_paper_by_arxiv_id(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    _user: CurrentUserRequired,
) -> PaperResponse:
    """Get a single paper by arXiv ID."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise ResourceNotFoundError("Paper", arxiv_id)
    return PaperResponse.model_validate(paper, from_attributes=True)


@router.get(
    "/papers/{arxiv_id}/score",
    response_model=PaperScoreDetailResponse,
    responses={202: {"model": ScorePendingResponse}},
)
async def get_paper_score(
    arxiv_id: str,
    user: CurrentUserRequired,
    feed_service: FeedServiceDep,
    redis: RedisDep,
    task_repo: TaskExecRepoDep,
    settings: SettingsDep,
) -> PaperScoreDetailResponse | JSONResponse:
    """The score breakdown for a paper; 202 while it is ingested and scored on demand.

    Opening a paper that is not scored yet enqueues `score_paper_task` (which ingests the
    full text itself). A Redis `SET NX` lock keyed on the arXiv id dedupes repeated polls
    into one task; the task releases it on completion and the TTL is the backstop.
    """
    if not _ARXIV_ID_RE.match(arxiv_id):
        raise InvalidParameterError("arxiv_id", arxiv_id, "not a valid arXiv identifier")

    detail = await feed_service.get_score_detail(user, arxiv_id)
    if detail is not None:
        return detail

    lock_key = ondemand_lock_key(arxiv_id)
    task_id = f"ondemand-{arxiv_id}-{uuid.uuid4().hex[:8]}"
    acquired = await redis.set(lock_key, task_id, nx=True, ex=settings.ondemand_score_lock_seconds)
    if acquired:
        score_paper_task.apply_async(kwargs={"arxiv_id": arxiv_id}, task_id=task_id)
        await task_repo.create(
            celery_task_id=task_id,
            user_id=user.id,
            task_type="score",
            parameters={"arxiv_id": arxiv_id, "on_demand": True},
        )
    else:
        held = await redis.get(lock_key)
        task_id = held.decode() if isinstance(held, bytes) else (held or None)

    pending = ScorePendingResponse(arxiv_id=arxiv_id, task_id=task_id)
    return JSONResponse(status_code=202, content=pending.model_dump())
