"""Tests for search router."""

import pytest


class TestSearchAuthentication:
    """Tests for search endpoint authentication."""

    def test_search_unauthenticated_returns_401(self, unauthenticated_client):
        """Test that unauthenticated requests return 401."""
        response = unauthenticated_client.post(
            "/api/v1/search", json={"query": "test query"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "MISSING_TOKEN"


class TestSearchEndpoint:
    """Tests for POST /api/v1/search endpoint."""

    def test_search_empty_results(self, client, mock_search_service):
        """Test search returns empty results."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post("/api/v1/search", json={"query": "test query"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []
        assert data["query"] == "test query"
        assert data["search_mode"] == "hybrid"

    def test_search_with_results(self, client, mock_search_service, sample_search_result):
        """Test search returns results."""
        mock_search_service.hybrid_search.return_value = [sample_search_result]

        response = client.post("/api/v1/search", json={"query": "machine learning"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["arxiv_id"] == "2301.00001"
        assert data["results"][0]["chunk_text"] == "Sample chunk text for testing."
        assert data["results"][0]["score"] == 0.95

    def test_search_with_custom_top_k(self, client, mock_search_service):
        """Test search with custom top_k parameter."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post(
            "/api/v1/search", json={"query": "test", "top_k": 20}
        )

        assert response.status_code == 200
        mock_search_service.hybrid_search.assert_called_once()
        call_kwargs = mock_search_service.hybrid_search.call_args.kwargs
        assert call_kwargs["top_k"] == 20

    def test_search_with_vector_mode(self, client, mock_search_service):
        """Test search with vector mode."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post(
            "/api/v1/search", json={"query": "test", "search_mode": "vector"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["search_mode"] == "vector"
        call_kwargs = mock_search_service.hybrid_search.call_args.kwargs
        assert call_kwargs["mode"] == "vector"

    def test_search_with_fulltext_mode(self, client, mock_search_service):
        """Test search with fulltext mode."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post(
            "/api/v1/search", json={"query": "test", "search_mode": "fulltext"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["search_mode"] == "fulltext"

    def test_search_with_min_score(self, client, mock_search_service):
        """Test search with minimum score filter."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post(
            "/api/v1/search", json={"query": "test", "min_score": 0.5}
        )

        assert response.status_code == 200
        call_kwargs = mock_search_service.hybrid_search.call_args.kwargs
        assert call_kwargs["min_score"] == 0.5

    def test_search_includes_execution_time(self, client, mock_search_service):
        """Test that execution time is included in response."""
        mock_search_service.hybrid_search.return_value = []

        response = client.post("/api/v1/search", json={"query": "test"})

        assert response.status_code == 200
        data = response.json()
        assert "execution_time_ms" in data
        assert data["execution_time_ms"] >= 0

    def test_search_invalid_top_k_too_high(self, client):
        """Test validation error for top_k exceeding maximum."""
        response = client.post(
            "/api/v1/search", json={"query": "test", "top_k": 100}
        )

        assert response.status_code == 422

    def test_search_invalid_top_k_too_low(self, client):
        """Test validation error for top_k below minimum."""
        response = client.post(
            "/api/v1/search", json={"query": "test", "top_k": 0}
        )

        assert response.status_code == 422

    def test_search_missing_query(self, client):
        """Test validation error for missing query."""
        response = client.post("/api/v1/search", json={})

        assert response.status_code == 422

    def test_search_invalid_search_mode(self, client):
        """Test validation error for invalid search mode."""
        response = client.post(
            "/api/v1/search", json={"query": "test", "search_mode": "invalid"}
        )

        assert response.status_code == 422

    def test_search_includes_vector_and_text_scores(
        self, client, mock_search_service, sample_search_result
    ):
        """Test that vector and text scores are included when available."""
        mock_search_service.hybrid_search.return_value = [sample_search_result]

        response = client.post("/api/v1/search", json={"query": "test"})

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]
        assert result["vector_score"] == 0.95
        # text_score is None in sample_search_result
        assert result["text_score"] is None
