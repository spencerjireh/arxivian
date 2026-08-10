"""Integration test: build_digest_for_week snapshots the right papers (SPE-271).

Real test DB + real repositories. Proves the selection boundaries that live in SQL (data
gate + week window) and in the task (category-set filter), the provisional-composite order,
and the upsert (a rebuild refreshes one row, never duplicates).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.models.digest import Digest
from src.models.paper_score import PaperScore
from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.tasks.digest_tasks import _category_key, _week_start, build_digest_for_week


async def _make_scored_paper(
    db_session, sample_paper_data, *, arxiv_id, categories, scores, created_at
):
    """Create a processed paper + a paper_scores row with an explicit created_at."""
    paper = await PaperRepository(db_session).create(
        {**sample_paper_data, "arxiv_id": arxiv_id, "categories": categories, "pdf_processed": True}
    )
    method, feasibility, data, demand = scores
    db_session.add(
        PaperScore(
            paper_id=paper.id,
            rubric_version="v1",
            method_clarity_score=method,
            resource_feasibility_score=feasibility,
            data_availability_score=data,
            demand_score=demand,
            details={},
            created_at=created_at,
        )
    )
    await db_session.flush()
    return paper


@pytest.mark.asyncio
async def test_build_digest_selects_and_orders(db_session, sample_paper_data):
    now = datetime.now(timezone.utc)
    week_start = _week_start(now.date())
    in_week = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
    before_week = in_week - timedelta(days=1)

    # composite 81.5 -- highest
    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-high",
        categories=["cs.LG"],
        scores=(80, 80, 100, 85),
        created_at=in_week,
    )
    # composite 37.5 -- lower
    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-low",
        categories=["cs.CL"],
        scores=(50, 40, 100, 20),
        created_at=in_week,
    )
    # gate FAIL -- excluded by the SQL query
    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-fail",
        categories=["cs.LG"],
        scores=(90, 90, 0, 80),
        created_at=in_week,
    )
    # category outside the digest set -- excluded by the task filter
    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-cv",
        categories=["cs.CV"],
        scores=(80, 80, 100, 80),
        created_at=in_week,
    )
    # scored before this week -- excluded by the week window
    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-old",
        categories=["cs.LG"],
        scores=(80, 80, 100, 80),
        created_at=before_week,
    )

    result = await build_digest_for_week(db_session, categories=["cs.LG", "cs.CL"], now=now)

    assert result["paper_count"] == 2
    digest = await DigestRepository(db_session).get_by_week(week_start, "cs.CL,cs.LG")
    assert digest is not None
    assert [entry["arxiv_id"] for entry in digest.ranking] == ["d-high", "d-low"]
    assert digest.ranking[0]["provisional_composite"] == 81.5


@pytest.mark.asyncio
async def test_rebuild_upserts_single_row(db_session, sample_paper_data):
    now = datetime.now(timezone.utc)
    week_start = _week_start(now.date())
    in_week = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)

    await _make_scored_paper(
        db_session,
        sample_paper_data,
        arxiv_id="d-only",
        categories=["cs.LG"],
        scores=(70, 70, 100, 55),
        created_at=in_week,
    )

    await build_digest_for_week(db_session, categories=["cs.LG"], now=now)
    await build_digest_for_week(db_session, categories=["cs.LG"], now=now)

    rows = (
        (
            await db_session.execute(
                select(Digest).where(
                    Digest.week_start == week_start,
                    Digest.category_key == _category_key(["cs.LG"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1  # upsert, not duplicate
    assert len(rows[0].ranking) == 1
