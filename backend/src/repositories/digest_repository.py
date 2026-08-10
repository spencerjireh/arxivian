"""Repository for the weekly digest snapshot (Stage 3, SPE-271).

One `digests` row per `(week_start, category_key)`. `upsert_digest` is idempotent so a
re-run of `build_digest_task` for the same week refreshes the ranking in place.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.digest import Digest
from src.utils.logger import get_logger

log = get_logger(__name__)


class DigestRepository:
    """Persists cached digest ranking snapshots with upsert-on-week semantics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_digest(
        self,
        *,
        week_start: date,
        category_key: str,
        categories: list[str],
        ranking: list[dict[str, Any]],
    ) -> Digest:
        """Insert or refresh the `(week_start, category_key)` snapshot.

        Returns the persisted Digest (flushed, not committed -- the caller owns commit).
        """
        existing = await self.get_by_week(week_start, category_key)
        if existing is None:
            digest = Digest(
                week_start=week_start,
                category_key=category_key,
                categories=categories,
                ranking=ranking,
            )
            self.session.add(digest)
        else:
            digest = existing
            digest.categories = categories
            digest.ranking = ranking

        await self.session.flush()
        log.info(
            "digest_upserted",
            week_start=week_start.isoformat(),
            category_key=category_key,
            paper_count=len(ranking),
            created=existing is None,
        )
        return digest

    async def get_by_week(self, week_start: date, category_key: str) -> Digest | None:
        """Fetch the cached snapshot for a week + category set, if built."""
        stmt = select(Digest).where(
            Digest.week_start == week_start,
            Digest.category_key == category_key,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
