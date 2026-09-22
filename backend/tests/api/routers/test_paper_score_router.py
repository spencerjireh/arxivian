"""Tests for GET /api/v1/papers/{arxiv_id}/score (detail + on-demand scoring)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import InvalidTokenError, PaperMetadataUnavailableError, ResourceNotFoundError
from src.schemas.feed import FeedScores
from src.schemas.papers import (
    DimensionDetail,
    PaperAttributesDetail,
    PaperMetadata,
    PaperScoreDetailResponse,
)


def _meta():
    return PaperMetadata(
        arxiv_id="2301.00001",
        title="T",
        authors=["A"],
        abstract="An abstract.",
        categories=["cs.LG"],
        published_date=datetime(2023, 1, 1, tzinfo=UTC),
        pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
    )


def _detail():
    return PaperScoreDetailResponse(
        paper=_meta(),
        rubric_version="v2",
        scored_at=datetime(2026, 8, 4, tzinfo=UTC),
        scores=FeedScores(
            method_clarity=80,
            resource_feasibility=80,
            data_availability=100,
            demand=85,
            composite=81.5,
        ),
        headline="Transformer for machine translation",
        meta=["one consumer GPU", "public data"],
        compute_match=None,
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
    def test_anonymous_scored_paper_returns_detail(self, unauthenticated_client, mock_feed_service):
        mock_feed_service.get_score_detail.return_value = _detail()
        resp = unauthenticated_client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 200
        assert resp.json()["paper"]["abstract"] == "An abstract."
        assert mock_feed_service.get_score_detail.await_args.args == (None, "2301.00001")

    def test_anonymous_unscored_paper_is_202_without_enqueue(
        self, unauthenticated_client, mock_feed_service, mock_task_exec_repo
    ):
        mock_feed_service.get_paper_metadata.return_value = _meta()
        redis = AsyncMock()
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = unauthenticated_client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending" and body["task_id"] is None
        assert body["paper"]["title"] == "T" and body["paper"]["abstract"] == "An abstract."
        task.apply_async.assert_not_called()
        redis.set.assert_not_awaited()
        redis.incr.assert_not_awaited()
        mock_task_exec_repo.create.assert_not_awaited()

    def test_invalid_token_is_still_401(self, unauthenticated_client, mock_feed_service):
        with patch("src.dependencies._sync_user", side_effect=InvalidTokenError("bad")):
            resp = unauthenticated_client.get(
                "/api/v1/papers/2301.00001/score", headers={"Authorization": "Bearer bad"}
            )
        assert resp.status_code == 401
        mock_feed_service.get_score_detail.assert_not_awaited()

    def test_unknown_id_is_404_without_enqueue(self, client, mock_feed_service):
        mock_feed_service.get_paper_metadata.side_effect = ResourceNotFoundError(
            "Paper", "2301.99999"
        )
        redis = AsyncMock()
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.99999/score")
        assert resp.status_code == 404
        task.apply_async.assert_not_called()
        redis.set.assert_not_awaited()

    def test_arxiv_outage_is_503_without_enqueue(self, client, mock_feed_service):
        mock_feed_service.get_paper_metadata.side_effect = PaperMetadataUnavailableError(
            "2301.00001"
        )
        redis = AsyncMock()
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "ARXIV_UNAVAILABLE"
        task.apply_async.assert_not_called()
        redis.set.assert_not_awaited()

    def test_returns_detail(self, client, mock_feed_service):
        mock_feed_service.get_score_detail.return_value = _detail()
        resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 200
        body = resp.json()
        assert body["rubric_version"] == "v2"
        assert body["headline"] == "Transformer for machine translation"
        assert body["meta"] == ["one consumer GPU", "public data"]
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
        mock_feed_service.get_paper_metadata.return_value = _meta()
        redis = AsyncMock()
        redis.set.return_value = True
        redis.incr.side_effect = [1, 1]
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending" and body["arxiv_id"] == "2301.00001"
        assert body["paper"]["title"] == "T"
        day = datetime.now(UTC).date().isoformat()
        incremented = [c.args[0] for c in redis.incr.await_args_list]
        assert incremented == [
            f"score:ondemand:day:{day}",
            f"score:ondemand:user:{mock_user.id}:{day}",
        ]
        assert redis.expire.await_count == 2
        redis.decr.assert_not_awaited()
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
        mock_feed_service.get_paper_metadata.return_value = _meta()
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
        redis.incr.assert_not_awaited()  # a poll never counts against the budgets

    @pytest.mark.parametrize(
        ("counts", "scope", "current", "limit"),
        [
            ([3, 11], "user", 10, 10),  # per-user cap (default 10) spent
            ([31, 4], "global", 30, 30),  # global budget (default 30) spent
        ],
    )
    def test_budget_spent_is_429_and_releases_the_lock(
        self, client, mock_feed_service, mock_task_exec_repo, counts, scope, current, limit
    ):
        mock_feed_service.get_score_detail.return_value = None
        mock_feed_service.get_paper_metadata.return_value = _meta()
        redis = AsyncMock()
        redis.set.return_value = True
        redis.incr.side_effect = counts
        _use_redis(redis)
        with patch("src.routers.papers.score_paper_task") as task:
            resp = client.get("/api/v1/papers/2301.00001/score")
        assert resp.status_code == 429
        error = resp.json()["error"]
        assert error["code"] == "SCORING_LIMIT_EXCEEDED"
        assert error["details"] == {"scope": scope, "current": current, "limit": limit}
        task.apply_async.assert_not_called()
        mock_task_exec_repo.create.assert_not_awaited()
        assert redis.decr.await_count == 2  # both counters undone
        redis.delete.assert_awaited_once_with("score:ondemand:2301.00001")

    def test_versioned_id_resolves_to_the_stored_row(self, client, mock_feed_service, mock_user):
        mock_feed_service.get_score_detail.return_value = _detail()
        assert client.get("/api/v1/papers/2301.00001v2/score").status_code == 200
        mock_feed_service.get_score_detail.assert_awaited_once_with(mock_user, "2301.00001")
