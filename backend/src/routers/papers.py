"""Papers management router."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.config import Settings
from src.dependencies import (
    CurrentUserRequired,
    FeedServiceDep,
    RedisDep,
    SettingsDep,
    TaskExecRepoDep,
)
from src.exceptions import InvalidParameterError, ScoringLimitExceededError
from src.schemas.papers import PaperScoreDetailResponse, ScorePendingResponse
from src.tasks.score_tasks import ondemand_budget_keys, ondemand_lock_key, score_paper_task

router = APIRouter()

# The budget keys name their day, so the TTL only cleans up; two days covers clock skew.
_BUDGET_KEY_TTL_SECONDS = 172_800

# New-style ids (2301.00001, 2301.00001v2). Old-style ids contain a slash and do not
# route through this path segment; they predate the feed and are not expected here.
_ARXIV_ID_RE = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?$")


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
        await _reserve_ondemand_slot(redis, user.id, settings, lock_key)
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


async def _reserve_ondemand_slot(
    redis: Redis, user_id: uuid.UUID, settings: Settings, lock_key: str
) -> None:
    """Count one on-demand score against today's global and per-user budgets (SPE-302).

    Runs only when this request is about to enqueue a new task, never for a poll that
    found the per-paper lock held. Past either budget it undoes the counts, releases the
    lock it just took, and raises the 429.
    """
    day_key, user_key = ondemand_budget_keys(user_id, datetime.now(UTC).date())
    day_count = int(await redis.incr(day_key))
    user_count = int(await redis.incr(user_key))
    await redis.expire(day_key, _BUDGET_KEY_TTL_SECONDS)
    await redis.expire(user_key, _BUDGET_KEY_TTL_SECONDS)

    if user_count > settings.ondemand_score_daily_per_user:
        scope, current, limit = "user", user_count - 1, settings.ondemand_score_daily_per_user
    elif day_count > settings.ondemand_score_daily_budget:
        scope, current, limit = "global", day_count - 1, settings.ondemand_score_daily_budget
    else:
        return

    await redis.decr(day_key)
    await redis.decr(user_key)
    await redis.delete(lock_key)
    raise ScoringLimitExceededError(scope=scope, current=current, limit=limit)
