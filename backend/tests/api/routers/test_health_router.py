"""Tests for health check router."""


class TestHealthEndpoint:
    """Tests for GET /api/v1/health endpoint."""

    def test_health_all_services_healthy(
        self, client, mock_paper_repo, mock_chunk_repo, mock_embeddings_client
    ):
        """Test healthy response when all services are up."""
        mock_paper_repo.count.return_value = 100
        mock_chunk_repo.count.return_value = 500

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" in data["services"]
        assert data["services"]["database"]["status"] == "healthy"
        assert data["services"]["database"]["details"]["papers_count"] == 100
        assert data["services"]["database"]["details"]["chunks_count"] == 500

    def test_health_includes_llm_status(self, client, mock_settings, monkeypatch):
        """Test that LLM provider status is included."""
        # Apply mock_settings to the health router (openai/gpt-4o-mini + key set),
        # mirroring test_health_degraded_on_missing_llm_key. Without this the fixture
        # is inert and the router reads the real settings.
        monkeypatch.setattr("src.routers.health.get_settings", lambda: mock_settings)

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "llm" in data["services"]
        assert data["services"]["llm"]["status"] == "healthy"
        assert "openai" in data["services"]["llm"]["message"]

    def test_health_includes_jina_status(self, client, mock_embeddings_client):
        """Test that Jina embeddings status is included."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "jina" in data["services"]
        assert data["services"]["jina"]["status"] == "healthy"

    def test_health_degraded_on_db_failure(self, client, mock_paper_repo):
        """Test degraded status when database fails."""
        mock_paper_repo.count.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"]["status"] == "unhealthy"
        assert data["services"]["database"]["message"] == "Service unavailable"

    def test_health_degraded_on_missing_llm_key(self, client, mock_settings, monkeypatch):
        """Test degraded status when LLM API key is missing."""
        mock_settings.openai_api_key = None
        monkeypatch.setattr("src.routers.health.get_settings", lambda: mock_settings)

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["llm"]["status"] == "unhealthy"

    def test_health_degraded_on_missing_jina_key(self, client, mock_embeddings_client):
        """Test degraded status when Jina API key is missing."""
        mock_embeddings_client.api_key = None

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["jina"]["status"] == "unhealthy"

    def test_health_includes_version(self, client):
        """Test that version is included in response."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.2.0"

    def test_health_includes_timestamp(self, client):
        """Test that timestamp is included in response."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")
