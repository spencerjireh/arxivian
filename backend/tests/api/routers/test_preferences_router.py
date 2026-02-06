"""API tests for preferences router endpoints."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, Mock, AsyncMock


class TestGetPreferencesEndpoint:
    """Tests for GET /api/v1/preferences endpoint."""

    def test_returns_empty_preferences_for_new_user(self, client, mock_user):
        """Verify empty preferences are returned for a user with no preferences."""
        # Ensure mock user has no preferences
        mock_user.preferences = None

        response = client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_searches"] == []
        assert "notification_settings" in data

    def test_returns_existing_preferences(self, client, mock_user):
        """Verify existing preferences are returned correctly."""
        mock_user.preferences = {
            "arxiv_searches": [
                {
                    "name": "ML Papers",
                    "query": "machine learning",
                    "categories": ["cs.LG"],
                    "max_results": 10,
                    "enabled": True,
                }
            ],
            "notification_settings": {"email_digest": True},
        }

        response = client.get("/api/v1/preferences")

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 1
        assert data["arxiv_searches"][0]["name"] == "ML Papers"
        assert data["arxiv_searches"][0]["query"] == "machine learning"

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/preferences")

        assert response.status_code == 401


class TestUpdateArxivSearchesEndpoint:
    """Tests for PUT /api/v1/preferences/arxiv-searches endpoint."""

    def test_replaces_all_searches(self, client, mock_user, mock_db_session):
        """Verify the endpoint replaces all existing searches."""
        mock_user.preferences = {
            "arxiv_searches": [
                {"name": "Old Search", "query": "old query", "enabled": True}
            ]
        }

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.put(
                "/api/v1/preferences/arxiv-searches",
                json={
                    "arxiv_searches": [
                        {
                            "name": "New Search 1",
                            "query": "new query 1",
                            "enabled": True,
                        },
                        {
                            "name": "New Search 2",
                            "query": "new query 2",
                            "enabled": False,
                        },
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 2
        assert data["arxiv_searches"][0]["name"] == "New Search 1"
        assert data["arxiv_searches"][1]["name"] == "New Search 2"

    def test_validates_search_config(self, client, mock_user):
        """Verify the endpoint validates search configuration."""
        # Empty query should fail validation
        response = client.put(
            "/api/v1/preferences/arxiv-searches",
            json={
                "arxiv_searches": [
                    {
                        "name": "Invalid Search",
                        "query": "",  # Empty query should fail
                        "enabled": True,
                    }
                ]
            },
        )

        assert response.status_code == 422  # Validation error

    def test_validates_name_length(self, client, mock_user):
        """Verify the endpoint validates name max length."""
        response = client.put(
            "/api/v1/preferences/arxiv-searches",
            json={
                "arxiv_searches": [
                    {
                        "name": "x" * 101,  # Exceeds max length
                        "query": "test query",
                        "enabled": True,
                    }
                ]
            },
        )

        assert response.status_code == 422

    def test_validates_max_results_range(self, client, mock_user):
        """Verify the endpoint validates max_results within range."""
        response = client.put(
            "/api/v1/preferences/arxiv-searches",
            json={
                "arxiv_searches": [
                    {
                        "name": "Test",
                        "query": "test query",
                        "max_results": 100,  # Exceeds max of 50
                        "enabled": True,
                    }
                ]
            },
        )

        assert response.status_code == 422

    def test_persists_changes_to_database(self, client, mock_user, mock_db_session):
        """Verify changes are persisted to the database."""
        mock_user.preferences = {}

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.put(
                "/api/v1/preferences/arxiv-searches",
                json={
                    "arxiv_searches": [
                        {"name": "Test", "query": "test query", "enabled": True}
                    ]
                },
            )

        assert response.status_code == 200
        # Verify update_preferences was called
        mock_repo.update_preferences.assert_called_once()
        # Verify commit was called
        mock_db_session.commit.assert_called()

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.put(
            "/api/v1/preferences/arxiv-searches",
            json={"arxiv_searches": []},
        )

        assert response.status_code == 401


class TestAddArxivSearchEndpoint:
    """Tests for POST /api/v1/preferences/arxiv-searches endpoint."""

    def test_adds_search_to_existing_list(self, client, mock_user, mock_db_session):
        """Verify search is added to existing list."""
        mock_user.preferences = {
            "arxiv_searches": [
                {"name": "Existing Search", "query": "existing query", "enabled": True}
            ]
        }

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.post(
                "/api/v1/preferences/arxiv-searches",
                json={
                    "name": "New Search",
                    "query": "new query",
                    "categories": ["cs.LG"],
                    "max_results": 15,
                    "enabled": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 2
        assert data["arxiv_searches"][0]["name"] == "Existing Search"
        assert data["arxiv_searches"][1]["name"] == "New Search"

    def test_creates_list_if_none_exists(self, client, mock_user, mock_db_session):
        """Verify list is created if user has no searches."""
        mock_user.preferences = None

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.post(
                "/api/v1/preferences/arxiv-searches",
                json={
                    "name": "First Search",
                    "query": "first query",
                    "enabled": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 1
        assert data["arxiv_searches"][0]["name"] == "First Search"

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/preferences/arxiv-searches",
            json={"name": "Test", "query": "test", "enabled": True},
        )

        assert response.status_code == 401

    def test_uses_default_max_results(self, client, mock_user, mock_db_session):
        """Verify default max_results is used when not specified."""
        mock_user.preferences = {}

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.post(
                "/api/v1/preferences/arxiv-searches",
                json={
                    "name": "Test",
                    "query": "test query",
                    "enabled": True,
                    # No max_results specified
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Default is 10 from schema
        assert data["arxiv_searches"][0]["max_results"] == 10


class TestDeleteArxivSearchEndpoint:
    """Tests for DELETE /api/v1/preferences/arxiv-searches/{search_name} endpoint."""

    def test_removes_search_by_name(self, client, mock_user, mock_db_session):
        """Verify search is removed by name."""
        mock_user.preferences = {
            "arxiv_searches": [
                {"name": "Keep This", "query": "keep query", "enabled": True},
                {"name": "Delete This", "query": "delete query", "enabled": True},
            ]
        }

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.delete("/api/v1/preferences/arxiv-searches/Delete%20This")

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 1
        assert data["arxiv_searches"][0]["name"] == "Keep This"

    def test_handles_nonexistent_search(self, client, mock_user, mock_db_session):
        """Verify endpoint handles deletion of non-existent search gracefully."""
        mock_user.preferences = {
            "arxiv_searches": [
                {"name": "Existing", "query": "query", "enabled": True}
            ]
        }

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.delete("/api/v1/preferences/arxiv-searches/NonExistent")

        # Should succeed but not change anything
        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 1
        assert data["arxiv_searches"][0]["name"] == "Existing"

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.delete("/api/v1/preferences/arxiv-searches/Test")

        assert response.status_code == 401

    def test_handles_empty_preferences(self, client, mock_user, mock_db_session):
        """Verify endpoint handles user with no preferences."""
        mock_user.preferences = None

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            response = client.delete("/api/v1/preferences/arxiv-searches/Test")

        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_searches"] == []

    def test_url_decodes_search_name(self, client, mock_user, mock_db_session):
        """Verify URL encoded search names are decoded correctly."""
        mock_user.preferences = {
            "arxiv_searches": [
                {"name": "ML & AI Papers", "query": "query", "enabled": True}
            ]
        }

        with patch("src.routers.preferences.UserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.update_preferences = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # URL encoded: "ML & AI Papers" -> "ML%20%26%20AI%20Papers"
            response = client.delete("/api/v1/preferences/arxiv-searches/ML%20%26%20AI%20Papers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 0
