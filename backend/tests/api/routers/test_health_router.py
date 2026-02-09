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

    def test_health_includes_llm_status(self, client, mock_settings):
        """Test that LLM provider status is included."""
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
        assert "Database connection failed" in data["services"]["database"]["message"]

    def test_health_degraded_on_missing_llm_key(
        self,
        mock_db_session,
        mock_paper_repo,
        mock_chunk_repo,
        mock_embeddings_client,
        monkeypatch,
    ):
        """Test degraded status when LLM API key is missing."""
        from src.main import app
        from src.database import get_db
        from src.dependencies import get_paper_repository, get_chunk_repository
        from src.factories.client_factories import get_embeddings_client
        from typing import AsyncGenerator
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import Mock
        from fastapi.testclient import TestClient

        # Create settings with missing LLM key
        bad_settings = Mock()
        bad_settings.default_llm_model = "openai/gpt-4o-mini"
        bad_settings.allowed_llm_models = "openai/gpt-4o-mini"
        bad_settings.openai_api_key = None
        bad_settings.nvidia_nim_api_key = None
        bad_settings.jina_api_key = "test-key"
        bad_settings.langfuse_enabled = False
        bad_settings.get_allowed_models_list = Mock(return_value=["openai/gpt-4o-mini"])

        # Monkeypatch get_settings in the health router module
        monkeypatch.setattr("src.routers.health.get_settings", lambda: bad_settings)

        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_paper_repository] = lambda: mock_paper_repo
        app.dependency_overrides[get_chunk_repository] = lambda: mock_chunk_repo
        app.dependency_overrides[get_embeddings_client] = lambda: mock_embeddings_client

        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/v1/health")

        app.dependency_overrides.clear()

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
