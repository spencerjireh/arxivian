"""Tests for the per-user paper state endpoints."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.schemas.feed import FeedItem, FeedPaper, LibraryResponse, UserPaperStateResponse


def _state_row(state="saved", repo_url=None, dismissal_reason=None):
    row = Mock()
    row.state = state
    row.repo_url = repo_url
    row.dismissal_reason = dismissal_reason
    row.updated_at = datetime(2026, 8, 5, tzinfo=UTC)
    return row


@pytest.mark.api
class TestPutPaperState:
    def test_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.put(
            "/api/v1/papers/2301.00001/state", json={"state": "saved"}
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize("state", ["saved", "dismissed", "implementing"])
    def test_upserts(
        self, client, mock_paper_repo, mock_state_repo, sample_paper, mock_user, state
    ):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        mock_state_repo.upsert.return_value = _state_row(state)
        resp = client.put("/api/v1/papers/2301.00001/state", json={"state": state})
        assert resp.status_code == 200
        assert resp.json()["state"] == state
        mock_state_repo.upsert.assert_awaited_once_with(
            user_id=mock_user.id,
            paper_id=sample_paper.id,
            state=state,
            repo_url=None,
            dismissal_reason=None,
        )

    def test_shipped_with_repo(self, client, mock_paper_repo, mock_state_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        mock_state_repo.upsert.return_value = _state_row("shipped", "https://github.com/a/b")
        resp = client.put(
            "/api/v1/papers/2301.00001/state",
            json={"state": "shipped", "repo_url": "https://github.com/a/b"},
        )
        assert resp.status_code == 200
        assert mock_state_repo.upsert.await_args.kwargs["repo_url"] == "https://github.com/a/b"

    def test_shipped_without_repo_is_422(self, client, mock_paper_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        resp = client.put("/api/v1/papers/2301.00001/state", json={"state": "shipped"})
        assert resp.status_code == 422

    def test_dismissal_reason_only_when_dismissed(self, client, mock_paper_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        resp = client.put(
            "/api/v1/papers/2301.00001/state", json={"state": "saved", "dismissal_reason": "x"}
        )
        assert resp.status_code == 422

    def test_unknown_state_is_422(self, client, mock_paper_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        resp = client.put("/api/v1/papers/2301.00001/state", json={"state": "archived"})
        assert resp.status_code == 422

    def test_unknown_paper_is_404(self, client, mock_paper_repo, mock_state_repo):
        mock_paper_repo.get_by_arxiv_id.return_value = None
        resp = client.put("/api/v1/papers/9999.99999/state", json={"state": "saved"})
        assert resp.status_code == 404
        mock_state_repo.upsert.assert_not_awaited()


@pytest.mark.api
class TestDeletePaperState:
    def test_deletes(self, client, mock_paper_repo, mock_state_repo, sample_paper, mock_user):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        mock_state_repo.delete.return_value = True
        resp = client.delete("/api/v1/papers/2301.00001/state")
        assert resp.status_code == 204
        mock_state_repo.delete.assert_awaited_once_with(mock_user.id, sample_paper.id)

    def test_no_row_is_404(self, client, mock_paper_repo, mock_state_repo, sample_paper):
        mock_paper_repo.get_by_arxiv_id.return_value = sample_paper
        mock_state_repo.delete.return_value = False
        assert client.delete("/api/v1/papers/2301.00001/state").status_code == 404

    def test_unknown_paper_is_404(self, client, mock_paper_repo):
        mock_paper_repo.get_by_arxiv_id.return_value = None
        assert client.delete("/api/v1/papers/9999.99999/state").status_code == 404


@pytest.mark.api
class TestGetLibrary:
    def test_requires_auth(self, unauthenticated_client):
        assert unauthenticated_client.get("/api/v1/users/me/library").status_code == 401

    def test_returns_grouped_cards(self, client, mock_feed_service, sample_paper, mock_user):
        item = FeedItem(
            paper=FeedPaper.model_validate(sample_paper),
            state=UserPaperStateResponse.model_validate(_state_row("shipped")),
        )
        mock_feed_service.get_library.return_value = LibraryResponse(
            saved=[], implementing=[], shipped=[item]
        )
        resp = client.get("/api/v1/users/me/library")
        assert resp.status_code == 200
        body = resp.json()
        assert body["saved"] == [] and body["implementing"] == []
        assert body["shipped"][0]["paper"]["arxiv_id"] == "2301.00001"
        assert body["shipped"][0]["state"]["state"] == "shipped"
        assert body["shipped"][0]["scores"] is None
        mock_feed_service.get_library.assert_awaited_once_with(mock_user)
