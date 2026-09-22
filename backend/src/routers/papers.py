"""Papers router: the score breakdown and on-demand scoring (public read, PUBLIC-1)."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.config import Settings
from src.dependencies import (
    CurrentUserOptional,
    FeedServiceDep,
    RedisDep,
    SettingsDep,
    TaskExecRepoDep,
)
from src.exceptions import InvalidParameterError, ScoringLimitExceededError
from src.models.user import User
from src.repositories.task_execution_repository import TaskExecutionRepository
from src.schemas.papers import PaperScoreDetailResponse, ScorePendingResponse
from src.tasks.score_tasks import ondemand_budget_keys, ondemand_lock_key, score_paper_task

router = APIRouter()

# The budget keys name their day, so the TTL only cleans up; two days covers clock skew.
_BUDGET_KEY_TTL_SECONDS = 172_800

# New-style ids (2301.00001, 2301.00001v2). Old-style ids contain a slash and do not
# route through this path segment; they predate the feed and are not expected here.
_ARXIV_ID_RE = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+(\.[A-Z]{2})?/\d{7})(v\d+)?$")
# Rows, lock keys and task ids are versionless (`ArxivPaper.arxiv_id` strips the suffix).
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


@router.get(
    "/papers/{arxiv_id}/score",
    response_model=PaperScoreDetailResponse,
    responses={202: {"model": ScorePendingResponse}},
)
async def get_paper_score(
    arxiv_id: str,
    user: CurrentUserOptional,
    feed_service: FeedServiceDep,
    redis: RedisDep,
    task_repo: TaskExecRepoDep,
    settings: SettingsDep,
) -> PaperScoreDetailResponse | JSONResponse:
    """The score breakdown for a paper; 202 with its metadata while it is unscored.

    Public. A signed-in caller opening an unscored paper enqueues `score_paper_task`
    (which ingests the full text itself) behind a Redis `SET NX` lock keyed on the arXiv
    id, so repeated polls share one task; the task releases the lock on completion and
    the TTL is the backstop. An anonymous caller gets the metadata only: nothing is
    enqueued and no budget is spent. A paper unknown to the index is fetched from arXiv
    (404 when arXiv has no entry, 503 when arXiv is down) and stored as a metadata-only row.
    """
    if not _ARXIV_ID_RE.match(arxiv_id):
        raise InvalidParameterError("arxiv_id", arxiv_id, "not a valid arXiv identifier")
    arxiv_id = _VERSION_SUFFIX_RE.sub("", arxiv_id)

    detail = await feed_service.get_score_detail(user, arxiv_id)
    if detail is not None:
        return detail

    paper = await feed_service.get_paper_metadata(arxiv_id)
    task_id = None
    if user is not None:
        task_id = await _enqueue_ondemand(redis, task_repo, settings, user, arxiv_id)

    pending = ScorePendingResponse(arxiv_id=arxiv_id, paper=paper, task_id=task_id)
    return JSONResponse(status_code=202, content=pending.model_dump(mode="json"))


async def _enqueue_ondemand(
    redis: Redis,
    task_repo: TaskExecutionRepository,
    settings: Settings,
    user: User,
    arxiv_id: str,
) -> str | None:
    """Start on-demand scoring for a signed-in caller, or report the task already running.

    Returns the task id that holds the per-paper lock: a new one when this request took
    the lock (after counting against the budgets), the held one when a task is already in
    flight, None when the lock is held but its owner could not be read.
    """
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
        return task_id

    held = await redis.get(lock_key)
    return held.decode() if isinstance(held, bytes) else (held or None)


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
