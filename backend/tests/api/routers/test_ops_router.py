"""Tests for ops router."""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest


class TestCleanupEndpoint:
    """Tests for POST /api/v1/ops/cleanup endpoint."""

    def test_cleanup_no_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup when no orphaned papers exist."""
        mock_paper_repo.get_orphaned_papers.return_value = []

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 0
        assert data["papers_deleted"] == 0
        assert data["deleted_papers"] == []

    def test_cleanup_with_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup deletes orphaned papers."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "Orphaned Paper"

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 1
        assert data["papers_deleted"] == 1
        assert len(data["deleted_papers"]) == 1
        assert data["deleted_papers"][0]["arxiv_id"] == "2301.00001"

    def test_cleanup_multiple_orphaned_papers(self, client, mock_paper_repo):
        """Test cleanup with multiple orphaned papers."""
        orphaned_papers = []
        for i in range(3):
            paper = Mock()
            paper.id = f"paper-uuid-{i}"
            paper.arxiv_id = f"2301.0000{i}"
            paper.title = f"Orphaned Paper {i}"
            orphaned_papers.append(paper)

        mock_paper_repo.get_orphaned_papers.return_value = orphaned_papers

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert data["orphaned_papers_found"] == 3
        assert data["papers_deleted"] == 3
        assert len(data["deleted_papers"]) == 3

    def test_cleanup_calls_delete_for_each_paper(self, client, mock_paper_repo):
        """Test that delete is called for each orphaned paper."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "Orphaned Paper"

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        mock_paper_repo.delete.assert_called_once_with("paper-uuid-1")

    def test_cleanup_truncates_long_titles(self, client, mock_paper_repo):
        """Test that long titles are truncated in response."""
        orphaned_paper = Mock()
        orphaned_paper.id = "paper-uuid-1"
        orphaned_paper.arxiv_id = "2301.00001"
        orphaned_paper.title = "A" * 200  # Very long title

        mock_paper_repo.get_orphaned_papers.return_value = [orphaned_paper]

        response = client.post("/api/v1/ops/cleanup")

        assert response.status_code == 200
        data = response.json()
        # Title should be truncated to 100 characters
        assert len(data["deleted_papers"][0]["title"]) == 100


class TestOpsAuthentication:
    """Tests for ops endpoint API key authentication."""

    def test_missing_api_key_returns_401(self, unauthenticated_client):
        """Test that missing API key returns 401."""
        response = unauthenticated_client.post("/api/v1/ops/cleanup")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, unauthenticated_client):
        """Test that an invalid API key returns 401."""
        response = unauthenticated_client.post(
            "/api/v1/ops/cleanup",
            headers={"X-Api-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_valid_api_key_returns_200(self, unauthenticated_client, mock_paper_repo):
        """Test that a valid API key authenticates successfully."""
        mock_paper_repo.get_orphaned_papers.return_value = []
        response = unauthenticated_client.post(
            "/api/v1/ops/cleanup",
            headers={"X-Api-Key": "test-api-key"},
        )
        assert response.status_code == 200


class TestBulkIngestEndpoint:
    """Tests for POST /api/v1/ops/ingest endpoint."""

    @pytest.fixture(autouse=True)
    def _mock_system_user(self):
        """Mock get_system_user_id for ingest tests."""
        with patch("src.routers.ops.get_system_user_id", return_value=uuid.uuid4()):
            yield

    @pytest.fixture(autouse=True)
    def _mock_celery_task(self):
        """Mock the Celery ingest task."""
        with patch("src.routers.ops.ingest_papers_task") as mock_task:
            mock_result = Mock()
            mock_result.id = "test-celery-task-id"
            mock_task.delay.return_value = mock_result
            self.mock_task = mock_task
            yield

    def test_ingest_by_arxiv_ids(self, client, mock_task_exec_repo):
        """Test ingestion by providing specific arXiv IDs."""
        response = client.post(
            "/api/v1/ops/ingest",
            json={"arxiv_ids": ["2301.00001", "2301.00002"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tasks_queued"] == 1
        assert len(data["task_ids"]) == 1
        mock_task_exec_repo.create.assert_called_once()
        # Verify delay() was called with a query built from the arxiv IDs
        self.mock_task.delay.assert_called_once()
        call_kwargs = self.mock_task.delay.call_args.kwargs
        assert "id:2301.00001" in call_kwargs["query"]
        assert "id:2301.00002" in call_kwargs["query"]
        assert call_kwargs["max_results"] == 2

    def test_ingest_by_search_query(self, client, mock_task_exec_repo):
        """Test ingestion by providing a search query."""
        response = client.post(
            "/api/v1/ops/ingest",
            json={"search_query": "transformer attention mechanism", "max_results": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tasks_queued"] == 1
        assert len(data["task_ids"]) == 1
        # Verify delay() was called with the correct query and max_results
        self.mock_task.delay.assert_called_once()
        call_kwargs = self.mock_task.delay.call_args.kwargs
        assert call_kwargs["query"] == "transformer attention mechanism"
        assert call_kwargs["max_results"] == 5

    def test_ingest_both(self, client, mock_task_exec_repo):
        """Test ingestion with both arXiv IDs and search query queues two tasks."""
        # Need unique task IDs for each call
        self.mock_task.delay.side_effect = [
            Mock(id="task-id-1"),
            Mock(id="task-id-2"),
        ]

        response = client.post(
            "/api/v1/ops/ingest",
            json={
                "arxiv_ids": ["2301.00001"],
                "search_query": "transformers",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tasks_queued"] == 2
        assert len(data["task_ids"]) == 2
        assert mock_task_exec_repo.create.call_count == 2

    def test_ingest_no_input(self, client):
        """Test that providing neither arxiv_ids nor search_query returns 422."""
        response = client.post(
            "/api/v1/ops/ingest",
            json={},
        )

        assert response.status_code == 422

    def test_ingest_requires_api_key(self, unauthenticated_client):
        """Test that ingestion requires API key authentication."""
        response = unauthenticated_client.post(
            "/api/v1/ops/ingest",
            json={"arxiv_ids": ["2301.00001"]},
        )

        assert response.status_code == 401


class TestOpsTaskEndpoints:
    """Tests for ops task management endpoints."""

    def test_list_tasks(self, client, mock_task_exec_repo):
        """Test listing all tasks returns paginated results."""
        task = Mock()
        task.celery_task_id = "test-task-123"
        task.task_type = "ingest"
        task.status = "queued"
        task.error_message = None
        task.created_at = datetime.now(timezone.utc)
        task.completed_at = None
        mock_task_exec_repo.list_all.return_value = ([task], 1)

        response = client.get("/api/v1/ops/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "test-task-123"

    def test_get_task_status(self, client, mock_task_exec_repo):
        """Test getting task status merges DB and Celery state."""
        task = Mock()
        task.celery_task_id = "test-task-123"
        task.task_type = "ingest"
        task.status = "queued"
        task.error_message = None
        task.created_at = datetime.now(timezone.utc)
        mock_task_exec_repo.get_by_celery_task_id.return_value = task

        with patch("src.routers.ops.AsyncResult") as mock_async_result:
            mock_result = Mock()
            mock_result.status = "PENDING"
            mock_result.ready.return_value = False
            mock_result.failed.return_value = False
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/ops/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["status"] == "pending"
        assert data["ready"] is False

    def test_get_task_not_found(self, client, mock_task_exec_repo):
        """Test getting nonexistent task returns 404."""
        mock_task_exec_repo.get_by_celery_task_id.return_value = None

        response = client.get("/api/v1/ops/tasks/nonexistent-task")

        assert response.status_code == 404

    def test_revoke_task(self, client, mock_task_exec_repo):
        """Test revoking a task."""
        task = Mock()
        task.celery_task_id = "test-task-123"
        mock_task_exec_repo.get_by_celery_task_id.return_value = task

        with patch("src.routers.ops.celery_app") as mock_celery:
            response = client.delete("/api/v1/ops/tasks/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["revoked"] is True
        mock_celery.control.revoke.assert_called_once_with("test-task-123", terminate=False)

    def test_revoke_task_not_found(self, client, mock_task_exec_repo):
        """Test revoking nonexistent task returns 404."""
        mock_task_exec_repo.get_by_celery_task_id.return_value = None

        response = client.delete("/api/v1/ops/tasks/nonexistent-task")

        assert response.status_code == 404


class TestGetSystemSearches:
    """Tests for GET /api/v1/ops/system/arxiv-searches endpoint."""

    def test_get_searches(self, client, mock_user_repo):
        """Test reading current system arXiv search configuration."""
        system_user = Mock()
        system_user.preferences = {
            "arxiv_searches": [
                {"name": "AI Papers", "query": "artificial intelligence", "max_results": 10, "enabled": True},
            ],
            "notification_settings": {},
        }
        mock_user_repo.get_by_clerk_id.return_value = system_user

        response = client.get("/api/v1/ops/system/arxiv-searches")

        assert response.status_code == 200
        data = response.json()
        assert len(data["arxiv_searches"]) == 1
        assert data["arxiv_searches"][0]["name"] == "AI Papers"

    def test_requires_api_key(self, unauthenticated_client):
        """Test that GET requires API key."""
        response = unauthenticated_client.get("/api/v1/ops/system/arxiv-searches")

        assert response.status_code == 401
