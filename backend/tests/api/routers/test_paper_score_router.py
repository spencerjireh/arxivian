"""Tests for GET /api/v1/papers/{arxiv_id}/score (detail + on-demand scoring)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.feed import FeedPaper, FeedScores, FeedSignals
from src.schemas.papers import DimensionDetail, PaperAttributesDetail, PaperScoreDetailResponse


def _detail():
    return PaperScoreDetailResponse(
        paper=FeedPaper(
            arxiv_id="2301.00001",
            title="T",
            authors=["A"],
            categories=["cs.LG"],
            published_date=datetime(2023, 1, 1, tzinfo=UTC),
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
        ),
        rubric_version="v2",
        scored_at=datetime(2026, 8, 4, tzinfo=UTC),
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
        low_confidence=["method_clarity"],
        state=None,
        attributes=PaperAttributesDetail(),
        dimensions=[
            DimensionDetail(
                dimension="method_clarity",
                band="HIGH",
                score=80,
                level=3,
                max_level=4,
                expected=3.2,
                probabilities={0: 0.0, 1: 0.0, 2: 0.2, 3: 0.4, 4: 0.4},
                confidence=0.4,
                judgments=[],
                evidence=[],
                reasoning="3 of 4 criteria",
            )
        ],
    )


def _use_redis(mock_redis):
    from src.dependencies import get_redis
    from src.main import app

    app.dependency_overrides[get_redis] = lambda: mock_redis


@pytest.mark.api
class TestGetPaperScore:
    def test_requires_auth(self, unauthenticated_client):
        assert unauthenticated_client.get("/api/v1/papers/2301.00001/score").status_code == 401

    def test_returns_detail(self, client, mock_feed_service):
        mock_feed_service.get_score_detail.return_value = _detail()
        resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 200
        body = resp.json()
        assert body["rubric_version"] == "v2"
        assert body["dimensions"][0]["dimension"] == "method_clarity"
        assert body["dimensions"][0]["probabilities"] == {
            "0": 0.0,
            "1": 0.0,
            "2": 0.2,
            "3": 0.4,
            "4": 0.4,
        }
        assert body["low_confidence"] == ["method_clarity"]

    def test_rejects_malformed_id_without_enqueue(self, client, mock_feed_service):
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/not-an-id/score")
        assert resp.status_code == 400
        task.apply_async.assert_not_called()
        mock_feed_service.get_score_detail.assert_not_awaited()

    def test_enqueues_when_lock_acquired(
        self, client, mock_feed_service, mock_task_exec_repo, mock_user
    ):
        mock_feed_service.get_score_detail.return_value = None
        redis = AsyncMock()
        redis.set.return_value = True
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending" and body["arxiv_id"] == "2301.00001"
        assert body["task_id"].startswith("ondemand-2301.00001-")
        redis.set.assert_awaited_once()
        assert redis.set.await_args.args[0] == "score:ondemand:2301.00001"
        assert redis.set.await_args.kwargs == {"nx": True, "ex": 1800}
        task.apply_async.assert_called_once_with(
            kwargs={"arxiv_id": "2301.00001"}, task_id=body["task_id"]
        )
        mock_task_exec_repo.create.assert_awaited_once_with(
            celery_task_id=body["task_id"],
            user_id=mock_user.id,
            task_type="score",
            parameters={"arxiv_id": "2301.00001", "on_demand": True},
        )

    def test_returns_held_task_when_lock_taken(
        self, client, mock_feed_service, mock_task_exec_repo
    ):
        mock_feed_service.get_score_detail.return_value = None
        redis = AsyncMock()
        redis.set.return_value = None
        redis.get.return_value = b"ondemand-2301.00001-abcd1234"
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "ondemand-2301.00001-abcd1234"
        task.apply_async.assert_not_called()
        mock_task_exec_repo.create.assert_not_awaited()

    def test_accepts_versioned_ids(self, client, mock_feed_service):
        mock_feed_service.get_score_detail.return_value = _detail()
        assert client.get("/api/v1/papers/2301.00001v2/score").status_code == 200
