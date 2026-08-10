"""Unit tests for the Stage 3 digest builder (SPE-271).

Exercises the category filter, provisional-composite ordering, and upsert shape with the DB
layer mocked. `list_scores_for_digest` already applies the gate + week filter at the SQL
layer, so the fabricated rows here are all gate-passing (that boundary is covered by the
integration test).
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from src.schemas.digest import compute_provisional_composite
from src.tasks.digest_tasks import _category_key, _week_start, build_digest_for_week

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)  # a Wednesday


def _score(method=None, feasibility=None, data=100, demand=None):
    return SimpleNamespace(
        method_clarity_score=method,
        resource_feasibility_score=feasibility,
        data_availability_score=data,
        demand_score=demand,
    )


def _paper(pid, arxiv_id, categories, title="T"):
    return SimpleNamespace(id=pid, arxiv_id=arxiv_id, title=title, categories=categories)


async def _run_build(rows, categories):
    """Invoke build_digest_for_week with the repositories patched; return (result, upsert_kwargs)."""
    scoring_repo = Mock()
    scoring_repo.list_scores_for_digest = AsyncMock(return_value=rows)

    digest_repo = Mock()
    digest_repo.upsert_digest = AsyncMock(return_value=SimpleNamespace(id="digest-uuid"))

    with (
        patch("src.tasks.digest_tasks.ScoringRepository", return_value=scoring_repo),
        patch("src.tasks.digest_tasks.DigestRepository", return_value=digest_repo),
    ):
        result = await build_digest_for_week(Mock(), categories=categories, now=NOW)

    return result, digest_repo.upsert_digest.call_args.kwargs


class TestBuildDigestForWeek:
    async def test_orders_by_provisional_composite_desc(self):
        rows = [
            (_score(40, 40, 100, 20), _paper("p-low", "2401.002", ["cs.LG"])),
            (_score(80, 80, 100, 85), _paper("p-high", "2401.001", ["cs.LG"])),
        ]
        result, kwargs = await _run_build(rows, ["cs.LG"])

        ranking = kwargs["ranking"]
        assert [e["arxiv_id"] for e in ranking] == ["2401.001", "2401.002"]
        assert result["paper_count"] == 2
        assert result["digest_id"] == "digest-uuid"

    async def test_filters_papers_outside_category_set(self):
        rows = [
            (_score(80, 80, 100, 85), _paper("p-in", "2401.001", ["cs.LG", "stat.ML"])),
            (_score(80, 80, 100, 85), _paper("p-out", "2401.002", ["cs.CV"])),
        ]
        _, kwargs = await _run_build(rows, ["cs.LG", "cs.CL"])

        ranking = kwargs["ranking"]
        assert [e["arxiv_id"] for e in ranking] == ["2401.001"]  # cs.CV paper excluded

    async def test_upsert_receives_week_start_and_category_key(self):
        rows = [(_score(80, 80, 100, 85), _paper("p1", "2401.001", ["cs.LG"]))]
        _, kwargs = await _run_build(rows, ["cs.CL", "cs.LG"])

        assert kwargs["week_start"] == _week_start(NOW.date())  # Monday 2026-08-03
        assert kwargs["category_key"] == "cs.CL,cs.LG"  # sorted-joined
        assert kwargs["categories"] == ["cs.CL", "cs.LG"]

    async def test_empty_when_no_scores(self):
        result, kwargs = await _run_build([], ["cs.LG"])
        assert result["paper_count"] == 0
        assert kwargs["ranking"] == []


class TestHelpers:
    def test_week_start_is_monday(self):
        assert _week_start(NOW.date()).isoformat() == "2026-08-03"  # Monday of that week

    def test_category_key_is_sorted(self):
        assert _category_key(["cs.LG", "cs.AI", "cs.CV"]) == "cs.AI,cs.CV,cs.LG"

    def test_composite_treats_nulls_as_zero(self):
        # 0.35*80 + 0.35*80 + 0.30*0 = 56.0
        assert compute_provisional_composite(80, 80, None) == 56.0
        assert compute_provisional_composite(None, None, None) == 0.0
