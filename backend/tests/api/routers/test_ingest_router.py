"""Tests for ingest router.

The /api/v1/ingest HTTP endpoint was removed in favour of ingestion via the
chat agent's ingest tool. These tests are kept for reference but skipped.
"""

import pytest
from unittest.mock import AsyncMock

from src.schemas.ingest import IngestResponse
from src.utils.idempotency import IdempotencyEntry

pytestmark = pytest.mark.skip(reason="Ingest HTTP endpoint removed -- ingestion via chat agent only")


class TestIngestEndpoint:
    """Tests for POST /api/v1/ingest endpoint."""

    def test_ingest_success(self, client, mock_ingest_service):
        """Test successful paper ingestion."""
        response = client.post(
            "/api/v1/ingest",
            json={"query": "machine learning", "max_results": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["papers_fetched"] == 1
        assert data["papers_processed"] == 1
        assert data["chunks_created"] == 10

    def test_ingest_with_filters(self, client, mock_ingest_service):
        """Test ingestion with category and date filters."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "transformers",
                "max_results": 10,
                "categories": ["cs.LG", "cs.CL"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
        )

        assert response.status_code == 200
        mock_ingest_service.ingest_papers.assert_called_once()

    def test_ingest_with_force_reprocess(self, client, mock_ingest_service):
        """Test ingestion with force_reprocess flag."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "bert",
                "force_reprocess": True,
            },
        )

        assert response.status_code == 200

    def test_ingest_returns_errors(self, client, mock_ingest_service):
        """Test that ingestion errors are included in response."""
        from src.schemas.ingest import PaperError

        mock_ingest_service.ingest_papers.return_value = IngestResponse(
            status="completed",
            papers_fetched=3,
            papers_processed=2,
            chunks_created=20,
            duration_seconds=5.0,
            errors=[PaperError(arxiv_id="2301.00002", error="Failed to download PDF")],
        )

        response = client.post(
            "/api/v1/ingest",
            json={"query": "neural networks"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["arxiv_id"] == "2301.00002"

    def test_ingest_missing_query(self, client):
        """Test validation error for missing query."""
        response = client.post("/api/v1/ingest", json={})

        assert response.status_code == 422

    def test_ingest_max_results_too_high(self, client):
        """Test validation error for max_results exceeding limit."""
        response = client.post(
            "/api/v1/ingest",
            json={"query": "test", "max_results": 100},
        )

        assert response.status_code == 422

    def test_ingest_max_results_too_low(self, client):
        """Test validation error for max_results below minimum."""
        response = client.post(
            "/api/v1/ingest",
            json={"query": "test", "max_results": 0},
        )

        assert response.status_code == 422


class TestIngestIdempotency:
    """Tests for idempotency handling in ingest endpoint."""

    def test_ingest_with_new_idempotency_key(self, client, mock_ingest_service):
        """Test ingestion with new idempotency key proceeds normally."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "attention mechanism",
                "idempotency_key": "unique-key-123",
            },
        )

        assert response.status_code == 200
        mock_ingest_service.ingest_papers.assert_called_once()

    def test_ingest_returns_cached_for_completed_key(self, client, mock_ingest_service):
        """Test that completed idempotency key returns cached response."""
        from src.utils.idempotency import idempotency_store

        # Pre-populate idempotency store with completed request
        cached_response = IngestResponse(
            status="completed",
            papers_fetched=5,
            papers_processed=5,
            chunks_created=50,
            duration_seconds=10.0,
            errors=[],
        )

        async def acquire_mock(key):
            return IdempotencyEntry(
                key=key, status="completed", response=cached_response
            )

        idempotency_store.acquire = acquire_mock

        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "test query",
                "idempotency_key": "completed-key",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["papers_fetched"] == 5
        assert data["chunks_created"] == 50
        # Service should NOT be called
        mock_ingest_service.ingest_papers.assert_not_called()

    def test_ingest_409_for_in_progress_key(self, client, mock_ingest_service):
        """Test 409 Conflict for in-progress idempotency key."""
        from src.utils.idempotency import idempotency_store

        async def acquire_mock(key):
            return IdempotencyEntry(key=key, status="in_progress")

        idempotency_store.acquire = acquire_mock

        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "test query",
                "idempotency_key": "in-progress-key",
            },
        )

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

    def test_ingest_idempotency_key_max_length(self, client):
        """Test validation error for idempotency key exceeding max length."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "query": "test",
                "idempotency_key": "A" * 65,  # Exceeds 64 char limit
            },
        )

        assert response.status_code == 422


class TestIngestErrorHandling:
    """Tests for error handling in ingest endpoint."""

    def test_ingest_rolls_back_on_exception(
        self, client, mock_ingest_service, mock_db_session
    ):
        """Test that database is rolled back on exception."""
        mock_ingest_service.ingest_papers.side_effect = Exception("Service error")

        response = client.post(
            "/api/v1/ingest",
            json={"query": "test"},
        )

        # Response should indicate error (500 or handled error format)
        assert response.status_code >= 400
        mock_db_session.rollback.assert_called()

    def test_ingest_service_exception_returns_error(
        self, client, mock_ingest_service
    ):
        """Test that service exception returns error response."""
        mock_ingest_service.ingest_papers.side_effect = Exception("Service error")

        response = client.post(
            "/api/v1/ingest",
            json={"query": "test"},
        )

        # Should return an error status code (500 or wrapped error)
        assert response.status_code >= 400
