"""Tests for /api/v1/users/me and the onboarding profile endpoint."""

from unittest.mock import Mock

import pytest


@pytest.mark.api
class TestGetMe:
    def test_requires_auth(self, unauthenticated_client):
        assert unauthenticated_client.get("/api/v1/users/me").status_code == 401

    def test_fresh_user_is_not_onboarded(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["onboarded"] is False
        assert body["preferences"] == {"feed_profile": None}
        assert body["chats_used_today"] == 0

    def test_profile_is_returned(self, client, mock_user):
        mock_user.preferences = {
            "arxiv_searches": [{"q": "x"}],
            "feed_profile": {
                "categories": ["cs.LG"],
                "compute_profile": "laptop",
                "keywords": ["rag"],
            },
        }
        body = client.get("/api/v1/users/me").json()
        assert body["onboarded"] is True
        assert body["preferences"]["feed_profile"] == {
            "categories": ["cs.LG"],
            "compute_profile": "laptop",
            "keywords": ["rag"],
            "weights": None,
        }

    def test_garbage_profile_reads_as_empty(self, client, mock_user):
        mock_user.preferences = {"feed_profile": {"categories": "nope"}}
        body = client.get("/api/v1/users/me").json()
        assert body["onboarded"] is False


@pytest.mark.api
class TestUpdatePreferences:
    def _updated_user(self, mock_user, merged):
        updated = Mock()
        for attr in ("id", "email", "first_name", "last_name", "tier"):
            setattr(updated, attr, getattr(mock_user, attr))
        updated.preferences = merged
        return updated

    def test_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.patch(
            "/api/v1/users/me/preferences",
            json={"categories": ["cs.LG"], "compute_profile": "laptop"},
        )
        assert resp.status_code == 401

    def test_writes_profile_and_preserves_other_keys(self, client, mock_user, mock_user_repo):
        mock_user.preferences = {"arxiv_searches": [{"q": "x"}]}
        mock_user_repo.update_preferences.side_effect = lambda user, prefs: self._updated_user(
            mock_user, prefs
        )
        resp = client.patch(
            "/api/v1/users/me/preferences",
            json={
                "categories": [" cs.LG", "cs.AI", "cs.LG"],
                "compute_profile": "single_gpu",
                "keywords": ["Attention", "attention", " sparse "],
            },
        )
        assert resp.status_code == 200
        merged = mock_user_repo.update_preferences.await_args.args[1]
        assert merged["arxiv_searches"] == [{"q": "x"}]
        assert merged["feed_profile"] == {
            "categories": ["cs.AI", "cs.LG"],
            "compute_profile": "single_gpu",
            "keywords": ["attention", "sparse"],
            "weights": None,
        }
        body = resp.json()
        assert body["onboarded"] is True
        assert body["preferences"]["feed_profile"]["compute_profile"] == "single_gpu"

    def test_keeps_existing_weights(self, client, mock_user, mock_user_repo):
        mock_user.preferences = {"feed_profile": {"weights": {"method_clarity": 1.0}}}
        mock_user_repo.update_preferences.side_effect = lambda user, prefs: self._updated_user(
            mock_user, prefs
        )
        client.patch(
            "/api/v1/users/me/preferences",
            json={"categories": ["cs.LG"], "compute_profile": "cloud"},
        )
        merged = mock_user_repo.update_preferences.await_args.args[1]
        assert merged["feed_profile"]["weights"] == {"method_clarity": 1.0}

    @pytest.mark.parametrize(
        "body",
        [
            {"categories": [], "compute_profile": "laptop"},
            {"categories": ["cs.LG"]},
            {"categories": ["cs.LG"], "compute_profile": "mainframe"},
            {"categories": ["CS LG"], "compute_profile": "laptop"},
            {"categories": ["cs.LG"], "compute_profile": "laptop", "keywords": ["x" * 51]},
            {"categories": ["cs.LG"], "compute_profile": "laptop", "weights": {"demand": 1}},
        ],
    )
    def test_rejects_bad_bodies(self, client, mock_user_repo, body):
        assert client.patch("/api/v1/users/me/preferences", json=body).status_code == 422
        mock_user_repo.update_preferences.assert_not_awaited()
