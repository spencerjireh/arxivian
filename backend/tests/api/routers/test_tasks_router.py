"""API tests for tasks router endpoints."""

import pytest
from unittest.mock import patch, Mock, AsyncMock


class TestIngestAsyncEndpoint:
    """Tests for POST /api/v1/tasks/ingest/async endpoint."""

    def test_queues_task_and_returns_task_id(self, client):
        """Verify the endpoint queues a task and returns task ID."""
        mock_task = Mock()
        mock_task.id = "test-task-id-123"

        with patch("src.routers.tasks.ingest_papers_task") as mock_ingest_task:
            mock_ingest_task.delay.return_value = mock_task

            response = client.post(
                "/api/v1/tasks/ingest/async",
                json={
                    "query": "machine learning",
                    "max_results": 10,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id-123"
        assert data["status"] == "queued"

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/tasks/ingest/async",
            json={"query": "test"},
        )

        assert response.status_code == 401

    def test_passes_all_request_params_to_task(self, client):
        """Verify all request parameters are passed to the task."""
        mock_task = Mock()
        mock_task.id = "test-task-id"

        with patch("src.routers.tasks.ingest_papers_task") as mock_ingest_task:
            mock_ingest_task.delay.return_value = mock_task

            response = client.post(
                "/api/v1/tasks/ingest/async",
                json={
                    "query": "deep learning",
                    "max_results": 25,
                    "categories": ["cs.LG", "cs.AI"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "force_reprocess": True,
                },
            )

        assert response.status_code == 200

        # Verify delay was called with correct parameters
        mock_ingest_task.delay.assert_called_once_with(
            query="deep learning",
            max_results=25,
            categories=["cs.LG", "cs.AI"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            force_reprocess=True,
        )

    def test_uses_default_values_for_optional_params(self, client):
        """Verify default values are used for optional parameters."""
        mock_task = Mock()
        mock_task.id = "test-task-id"

        with patch("src.routers.tasks.ingest_papers_task") as mock_ingest_task:
            mock_ingest_task.delay.return_value = mock_task

            response = client.post(
                "/api/v1/tasks/ingest/async",
                json={"query": "test query"},
            )

        assert response.status_code == 200

        # Check the call had defaults applied
        call_kwargs = mock_ingest_task.delay.call_args.kwargs
        assert call_kwargs["query"] == "test query"
        # Default max_results should be applied from IngestRequest schema


class TestGetTaskStatusEndpoint:
    """Tests for GET /api/v1/tasks/{task_id} endpoint."""

    def test_returns_pending_status(self, client):
        """Verify pending status is returned correctly."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "PENDING"
            mock_result.ready.return_value = False
            mock_result.successful.return_value = False
            mock_result.failed.return_value = False
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/pending-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "pending-task-123"
        assert data["status"] == "pending"
        assert data["ready"] is False
        assert data["result"] is None
        assert data["error"] is None

    def test_returns_started_status(self, client):
        """Verify started status is returned correctly."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "STARTED"
            mock_result.ready.return_value = False
            mock_result.successful.return_value = False
            mock_result.failed.return_value = False
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/started-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["ready"] is False

    def test_returns_success_status(self, client):
        """Verify success status is returned correctly."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "SUCCESS"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_result.failed.return_value = False
            mock_result.result = {"papers_processed": 5}
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/success-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ready"] is True
        # Result not included unless requested
        assert data["result"] is None

    def test_returns_success_status_with_result(self, client):
        """Verify result is included when requested."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "SUCCESS"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_result.failed.return_value = False
            mock_result.result = {"papers_processed": 5, "chunks_created": 50}
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/success-task-123?include_result=true")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"] == {"papers_processed": 5, "chunks_created": 50}

    def test_returns_failure_status_with_error(self, client):
        """Verify failure status includes error message."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "FAILURE"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = False
            mock_result.failed.return_value = True
            mock_result.result = Exception("Task failed: network error")
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/failed-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failure"
        assert data["ready"] is True
        assert "network error" in data["error"]

    def test_returns_retry_status(self, client):
        """Verify retry status is returned correctly."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "RETRY"
            mock_result.ready.return_value = False
            mock_result.successful.return_value = False
            mock_result.failed.return_value = False
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/retry-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "retry"
        assert data["ready"] is False

    def test_handles_unknown_status(self, client):
        """Verify unknown status is mapped to pending."""
        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "UNKNOWN_STATUS"
            mock_result.ready.return_value = False
            mock_result.successful.return_value = False
            mock_result.failed.return_value = False
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/unknown-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"


class TestRevokeTaskEndpoint:
    """Tests for DELETE /api/v1/tasks/{task_id} endpoint."""

    def test_revokes_task(self, client):
        """Verify the endpoint revokes a task."""
        with patch("src.routers.tasks.celery_app") as mock_celery:
            response = client.delete("/api/v1/tasks/task-to-revoke-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-to-revoke-123"
        assert data["revoked"] is True
        assert data["terminated"] is False

        mock_celery.control.revoke.assert_called_once_with(
            "task-to-revoke-123", terminate=False
        )

    def test_terminates_running_task_when_requested(self, client):
        """Verify terminate flag is passed to revoke."""
        with patch("src.routers.tasks.celery_app") as mock_celery:
            response = client.delete("/api/v1/tasks/task-to-terminate-123?terminate=true")

        assert response.status_code == 200
        data = response.json()
        assert data["terminated"] is True

        mock_celery.control.revoke.assert_called_once_with(
            "task-to-terminate-123", terminate=True
        )

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.delete("/api/v1/tasks/task-123")

        assert response.status_code == 401
