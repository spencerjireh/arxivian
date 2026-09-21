"""Nightly demand backfill (SPE-284).

The demand dimension is a Semantic Scholar lookup that soft-fails to NULL when the
keyless pool rate-limits us. The composite already renormalizes over present sub-scores,
so a NULL is harmless for ranking, but the signal is still worth having. This task walks
scores with `demand_score IS NULL` (oldest first, capped per run) and retries the lookup
sequentially; the client's Redis slot gate spaces the calls. Follows the `build_digest_task`
driver shape: no bind/retry, owns its commit.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.clients.semantic_scholar_client import SemanticScholarClient
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.factories import get_semantic_scholar_client
from src.repositories.scoring_repository import ScoringRepository
from src.services.scoring_service.judgments import demand_from_band
from src.services.scoring_service.state import DEMAND_BAND_TO_SCORE, RUBRIC_VERSION, EvidenceSpan
from src.tasks.runtime import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)


async def backfill_demand(
    session: AsyncSession,
    client: SemanticScholarClient,
    *,
    batch_size: int,
) -> dict[str, Any]:
    """Retry the demand lookup for up to `batch_size` NULL-demand scores.

    A lookup that fails again is logged and skipped (the next run retries it); the
    batch keeps going. Flushes only -- the caller owns commit.
    """
    repo = ScoringRepository(session)
    rows = await repo.list_missing_demand(rubric_version=RUBRIC_VERSION, limit=batch_size)

    filled = 0
    failed = 0
    for score, paper in rows:
        try:
            metrics = await client.get_citation_metrics(paper.arxiv_id)
        except Exception as e:
            failed += 1
            log.warning("demand_backfill_lookup_failed", arxiv_id=paper.arxiv_id, error=str(e))
            continue

        evidence = [
            EvidenceSpan(
                text=(
                    f"{metrics.citation_count} citations "
                    f"({metrics.influential_citation_count} influential), "
                    f"{metrics.citations_per_month} citations/month (band {metrics.demand_band})"
                ),
                kind="citation",
                source="Semantic Scholar",
            )
        ]
        reasoning = (
            f"Citation velocity {metrics.citations_per_month}/month maps to band "
            f"{metrics.demand_band} -> demand {DEMAND_BAND_TO_SCORE[metrics.demand_band]} "
            f"(backfilled)."
        )
        result = demand_from_band(metrics.demand_band, evidence, reasoning)
        await repo.set_demand(
            score,
            demand_score=result.derived_score(),
            dimension=result.model_dump(mode="json"),
            evidence=[
                {"dimension": "demand", "kind": e.kind, "text": e.text, "source": e.source}
                for e in evidence
            ],
        )
        filled += 1

    return {"candidates": len(rows), "filled": filled, "failed": failed}


@celery_app.task(name="src.tasks.demand_tasks.backfill_demand_task")
def backfill_demand_task() -> dict[str, Any]:
    """Fill in NULL demand scores left by rate-limited Semantic Scholar lookups."""
    log.info("demand_backfill_started")

    async def _run() -> dict[str, Any]:
        settings = get_settings()
        async with AsyncSessionLocal() as session:
            result = await backfill_demand(
                session,
                get_semantic_scholar_client(),
                batch_size=settings.demand_backfill_batch_size,
            )
            await session.commit()
        return {"status": "completed", **result}

    result = run_async(_run())
    log.info("demand_backfill_completed", **{k: v for k, v in result.items() if k != "status"})
    return result
