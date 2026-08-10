"""Stage 3 driver: build the weekly digest snapshot (SPE-271).

Snapshots this ISO week's gate-passing scored papers into a cached `digests` ranking so past
weeks render without recomputation. The per-user weighted composite + compute-profile match
are applied at read time (SPE-274), not here -- the baked order is a provisional default only.
Scheduled after `weekly-triage` so scored papers exist. Follows the `daily_ingest_task` /
`triage_new_papers_task` driver shape (no bind/retry; owns its commit).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.repositories.digest_repository import DigestRepository
from src.repositories.scoring_repository import ScoringRepository
from src.schemas.digest import DigestRankingEntry, compute_provisional_composite
from src.schemas.scoring_state import RUBRIC_VERSION
from src.tasks.utils import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


def _week_start(today: date) -> date:
    """Monday of `today`'s ISO week."""
    return today - timedelta(days=today.weekday())


def _category_key(categories: list[str]) -> str:
    """Stable key for the category set (matches the `digests` unique constraint)."""
    return ",".join(sorted(categories))


async def build_digest_for_week(
    session: AsyncSession,
    *,
    categories: list[str],
    now: datetime,
) -> dict[str, Any]:
    """Build (or refresh) the digest snapshot for `now`'s ISO week and `categories`.

    Selects gate-passing scores created in the week, keeps those whose categories intersect
    the set, ranks them by provisional composite, and upserts the `digests` row. Flushes but
    does NOT commit -- the caller owns the transaction. Injectable `now`/`categories` keep it
    deterministic under test.
    """
    category_set = set(categories)
    category_key = _category_key(categories)

    week_start = _week_start(now.date())
    start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=7)

    rows = await ScoringRepository(session).list_scores_for_digest(
        start=start_dt, end=end_dt, rubric_version=RUBRIC_VERSION
    )

    entries: list[DigestRankingEntry] = []
    for score, paper in rows:
        # Keep papers whose categories intersect the digest's configured set.
        if category_set.isdisjoint(paper.categories or []):
            continue
        entries.append(
            DigestRankingEntry(
                paper_id=str(paper.id),
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                method_clarity_score=score.method_clarity_score,
                resource_feasibility_score=score.resource_feasibility_score,
                data_availability_score=score.data_availability_score,
                demand_score=score.demand_score,
                provisional_composite=compute_provisional_composite(
                    score.method_clarity_score,
                    score.resource_feasibility_score,
                    score.demand_score,
                ),
            )
        )

    entries.sort(key=lambda e: e.provisional_composite, reverse=True)
    ranking = [entry.model_dump() for entry in entries]

    digest = await DigestRepository(session).upsert_digest(
        week_start=week_start,
        category_key=category_key,
        categories=categories,
        ranking=ranking,
    )
    return {
        "digest_id": str(digest.id),  # captured pre-commit while the instance is live
        "week_start": week_start.isoformat(),
        "category_key": category_key,
        "paper_count": len(ranking),
    }


@celery_app.task(name="src.tasks.digest_tasks.build_digest_task")
def build_digest_task() -> dict[str, Any]:
    """Build (or refresh) the current week's digest snapshot for the configured categories."""
    log.info("build_digest_started")

    async def _run() -> dict[str, Any]:
        settings = get_settings()
        async with AsyncSessionLocal() as session:
            result = await build_digest_for_week(
                session,
                categories=settings.triage_categories,
                now=datetime.now(timezone.utc),
            )
            await session.commit()
        return {"status": "completed", **result}

    result = run_async(_run())
    log.info(
        "build_digest_completed",
        week_start=result["week_start"],
        category_key=result["category_key"],
        paper_count=result["paper_count"],
    )
    return result
