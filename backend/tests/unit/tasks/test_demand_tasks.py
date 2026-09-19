"""Tests for the nightly demand backfill (SPE-284)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.clients.semantic_scholar_client import CitationMetrics
from src.tasks.demand_tasks import backfill_demand


def _metrics(arxiv_id: str, band: str, velocity: float) -> CitationMetrics:
    return CitationMetrics(
        arxiv_id=arxiv_id,
        found=True,
        citation_count=100,
        influential_citation_count=10,
        publication_date="2024-01-01",
        citations_per_month=velocity,
        demand_band=band,
    )


def _row(arxiv_id: str):
    score = SimpleNamespace(paper_id=f"pid-{arxiv_id}", dimensions={"method_clarity": {}})
    paper = SimpleNamespace(arxiv_id=arxiv_id)
    return score, paper


@pytest.mark.unit
class TestBackfillDemand:
    async def test_fills_each_candidate_and_skips_failures(self):
        rows = [_row("a"), _row("b"), _row("c")]
        repo = AsyncMock()
        repo.list_missing_demand.return_value = rows
        client = AsyncMock()
        client.get_citation_metrics.side_effect = [
            _metrics("a", "HIGH", 12.0),
            RuntimeError("429 again"),
            _metrics("c", "LOW", 0.1),
        ]

        with patch("src.tasks.demand_tasks.ScoringRepository", return_value=repo):
            result = await backfill_demand(AsyncMock(), client, batch_size=50)

        assert result == {"candidates": 3, "filled": 2, "failed": 1}
        repo.list_missing_demand.assert_awaited_once_with(rubric_version="v2", limit=50)
        assert repo.set_demand.await_count == 2

        first = repo.set_demand.await_args_list[0]
        assert first.args[0] is rows[0][0]
        assert first.kwargs["demand_score"] == 85
        assert first.kwargs["dimension"]["dimension"] == "demand"
        assert first.kwargs["dimension"]["level"] == 2
        assert first.kwargs["dimension"]["probabilities"] == {"0": 0.0, "1": 0.0, "2": 1.0}
        assert "backfilled" in first.kwargs["dimension"]["reasoning"]
        assert first.kwargs["evidence"] == [
            {
                "dimension": "demand",
                "kind": "citation",
                "text": "100 citations (10 influential), 12.0 citations/month (band HIGH)",
                "source": "Semantic Scholar",
            }
        ]
        assert repo.set_demand.await_args_list[1].kwargs["demand_score"] == 20

    async def test_nothing_to_do(self):
        repo = AsyncMock()
        repo.list_missing_demand.return_value = []
        client = AsyncMock()
        with patch("src.tasks.demand_tasks.ScoringRepository", return_value=repo):
            result = await backfill_demand(AsyncMock(), client, batch_size=10)
        assert result == {"candidates": 0, "filled": 0, "failed": 0}
        client.get_citation_metrics.assert_not_called()
