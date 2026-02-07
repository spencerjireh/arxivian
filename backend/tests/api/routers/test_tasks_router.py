"""API tests for tasks router endpoints."""

from datetime import datetime, timezone

import pytest
from unittest.mock import patch, Mock


class TestIngestAsyncEndpoint:
    """Tests for POST /api/v1/tasks/ingest/async endpoint."""

    def test_queues_task_and_returns_task_id(self, client, mock_task_exec_repo):
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
        assert data["task_type"] == "ingest"

    def test_creates_task_execution_record(self, client, mock_task_exec_repo, mock_user):
        """Verify task execution record is created in the database."""
        mock_task = Mock()
        mock_task.id = "test-task-id-123"

        with patch("src.routers.tasks.ingest_papers_task") as mock_ingest_task:
            mock_ingest_task.delay.return_value = mock_task

            response = client.post(
                "/api/v1/tasks/ingest/async",
                json={"query": "machine learning", "max_results": 10},
            )

        assert response.status_code == 200
        mock_task_exec_repo.create.assert_called_once_with(
            celery_task_id="test-task-id-123",
            user_id=mock_user.id,
            task_type="ingest",
            parameters={
                "query": "machine learning",
                "max_results": 10,
                "categories": None,
                "start_date": None,
                "end_date": None,
                "force_reprocess": False,
            },
        )

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/tasks/ingest/async",
            json={"query": "test"},
        )

        assert response.status_code == 401

    def test_passes_all_request_params_to_task(self, client, mock_task_exec_repo):
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

    def test_uses_default_values_for_optional_params(self, client, mock_task_exec_repo):
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

    @pytest.mark.parametrize(
        "celery_status,expected,ready,failed",
        [
            ("PENDING", "pending", False, False),
            ("STARTED", "started", False, False),
            ("SUCCESS", "success", True, False),
            ("FAILURE", "failure", True, True),
            ("RETRY", "retry", False, False),
            ("REVOKED", "revoked", True, False),
        ],
    )
    def test_maps_celery_status(
        self,
        client,
        mock_task_exec_repo,
        sample_task_execution,
        celery_status,
        expected,
        ready,
        failed,
    ):
        """Verify Celery status is mapped correctly to response status."""
        task_exec = sample_task_execution(task_id="status-task-123")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

        with patch("src.routers.tasks.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = celery_status
            mock_result.ready.return_value = ready
            mock_result.successful.return_value = celery_status == "SUCCESS"
            mock_result.failed.return_value = failed
            if failed:
                mock_result.result = Exception("error")
            else:
                mock_result.result = {"papers_processed": 5}
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/tasks/status-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == expected
        assert data["ready"] is ready

    def test_returns_success_status_with_result(
        self, client, mock_task_exec_repo, sample_task_execution
    ):
        """Verify result is included when requested."""
        task_exec = sample_task_execution(task_id="success-task-123")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

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

    def test_returns_failure_status_with_error(
        self, client, mock_task_exec_repo, sample_task_execution
    ):
        """Verify failure status includes error message."""
        task_exec = sample_task_execution(task_id="failed-task-123")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

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

    def test_handles_unknown_status(self, client, mock_task_exec_repo, sample_task_execution):
        """Verify unknown status falls back to DB record status."""
        task_exec = sample_task_execution(task_id="unknown-task-123", status="queued")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

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
        assert data["status"] == "queued"

    def test_returns_404_when_not_owned(self, client, mock_task_exec_repo, mock_user):
        """Verify 404 when task is not owned by the current user."""
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = None

        response = client.get("/api/v1/tasks/not-my-task-123")

        assert response.status_code == 404
        mock_task_exec_repo.get_by_user_and_celery_task_id.assert_called_once_with(
            mock_user.id, "not-my-task-123"
        )

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/task-123")

        assert response.status_code == 401


class TestRevokeTaskEndpoint:
    """Tests for DELETE /api/v1/tasks/{task_id} endpoint."""

    def test_revokes_task(self, client, mock_task_exec_repo, sample_task_execution):
        """Verify the endpoint revokes a task."""
        task_exec = sample_task_execution(task_id="task-to-revoke-123")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

        with patch("src.routers.tasks.celery_app") as mock_celery:
            response = client.delete("/api/v1/tasks/task-to-revoke-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-to-revoke-123"
        assert data["revoked"] is True
        assert data["terminated"] is False

        mock_celery.control.revoke.assert_called_once_with("task-to-revoke-123", terminate=False)

    def test_terminates_running_task_when_requested(
        self, client, mock_task_exec_repo, sample_task_execution
    ):
        """Verify terminate flag is passed to revoke."""
        task_exec = sample_task_execution(task_id="task-to-terminate-123")
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = task_exec

        with patch("src.routers.tasks.celery_app") as mock_celery:
            response = client.delete("/api/v1/tasks/task-to-terminate-123?terminate=true")

        assert response.status_code == 200
        data = response.json()
        assert data["terminated"] is True

        mock_celery.control.revoke.assert_called_once_with("task-to-terminate-123", terminate=True)

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.delete("/api/v1/tasks/task-123")

        assert response.status_code == 401

    def test_returns_404_when_not_owned(self, client, mock_task_exec_repo, mock_user):
        """Verify 404 when task is not owned by the current user."""
        mock_task_exec_repo.get_by_user_and_celery_task_id.return_value = None

        response = client.delete("/api/v1/tasks/not-my-task-123")

        assert response.status_code == 404
        mock_task_exec_repo.get_by_user_and_celery_task_id.assert_called_once_with(
            mock_user.id, "not-my-task-123"
        )


class TestListTasksEndpoint:
    """Tests for GET /api/v1/tasks/ endpoint."""

    def test_returns_empty_list(self, client, mock_task_exec_repo):
        """Verify empty task list is returned."""
        mock_task_exec_repo.list_by_user.return_value = ([], 0)

        response = client.get("/api/v1/tasks/")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_returns_paginated_tasks(self, client, mock_task_exec_repo):
        """Verify tasks are returned with pagination."""
        task1 = Mock()
        task1.celery_task_id = "task-1"
        task1.task_type = "ingest"
        task1.status = "success"
        task1.error_message = None
        task1.created_at = datetime.now(timezone.utc)
        task1.completed_at = datetime.now(timezone.utc)

        mock_task_exec_repo.list_by_user.return_value = ([task1], 1)

        response = client.get("/api/v1/tasks/?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "task-1"
        assert data["tasks"][0]["task_type"] == "ingest"
        assert data["tasks"][0]["status"] == "success"
        assert data["total"] == 1

    def test_requires_authentication(self, unauthenticated_client):
        """Verify the endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/tasks/")

        assert response.status_code == 401
