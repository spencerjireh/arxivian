"""Tests for GET /api/v1/feed."""

from datetime import date, datetime, timezone

import pytest

from src.schemas.feed import (
    AvailableWeek,
    FeedItem,
    FeedPaper,
    FeedResponse,
    FeedScores,
    FeedSignals,
)


def _response(items=()):
    return FeedResponse(
        week_start=date(2026, 8, 3),
        available_weeks=[AvailableWeek(week_start=date(2026, 8, 3), paper_count=len(items))],
        categories_available=["cs.LG"],
        total=len(items),
        offset=0,
        limit=20,
        items=list(items),
    )


def _item():
    return FeedItem(
        paper=FeedPaper(
            arxiv_id="2301.00001",
            title="T",
            authors=["A"],
            categories=["cs.LG"],
            published_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
        ),
        scores=FeedScores(
            method_clarity=80,
            resource_feasibility=80,
            data_availability=100,
            demand=85,
            composite=81.5,
        ),
        verdict="Transformer for machine translation; one consumer GPU; public data",
        signals=FeedSignals(
            pseudocode_present=True, public_datasets=True, single_gpu=True, code_released=False
        ),
        scored_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
    )


@pytest.mark.api
class TestGetFeed:
    def test_requires_auth(self, unauthenticated_client):
        assert unauthenticated_client.get("/api/v1/feed").status_code == 401

    def test_returns_page(self, client, mock_feed_service):
        mock_feed_service.get_feed.return_value = _response([_item()])
        resp = client.get("/api/v1/feed")
        assert resp.status_code == 200
        body = resp.json()
        assert body["week_start"] == "2026-08-03"
        assert body["total"] == 1
        assert body["items"][0]["paper"]["arxiv_id"] == "2301.00001"
        assert body["items"][0]["verdict"].startswith("Transformer")
        assert body["items"][0]["signals"]["compute_match"] is None
        assert body["items"][0]["state"] is None

    def test_forwards_query_params(self, client, mock_feed_service, mock_user):
        mock_feed_service.get_feed.return_value = _response()
        resp = client.get(
            "/api/v1/feed?week=2026-08-05&category=cs.LG&category=cs.CV&min_score=40"
            "&include_dismissed=true&offset=10&limit=5"
        )
        assert resp.status_code == 200
        mock_feed_service.get_feed.assert_awaited_once_with(
            mock_user,
            week=date(2026, 8, 5),
            categories=["cs.LG", "cs.CV"],
            min_score=40,
            include_dismissed=True,
            offset=10,
            limit=5,
        )

    @pytest.mark.parametrize(
        "query", ["limit=0", "limit=101", "min_score=101", "offset=-1", "week=foo"]
    )
    def test_rejects_bad_query(self, client, query):
        assert client.get(f"/api/v1/feed?{query}").status_code == 422

    def test_future_week_is_400(self, client, mock_feed_service):
        resp = client.get("/api/v1/feed?week=2999-01-01")
        assert resp.status_code == 400
        mock_feed_service.get_feed.assert_not_awaited()
