"""Unit tests for cleanup background tasks."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock, AsyncMock
from contextlib import asynccontextmanager


class TestCleanupTask:
    """Tests for the cleanup_task."""

    @pytest.fixture
    def mock_settings_30_days(self):
        """Mock settings with 30 day retention."""
        settings = Mock()
        settings.cleanup_retention_days = 30
        return settings

    @pytest.fixture
    def mock_settings_7_days(self):
        """Mock settings with 7 day retention."""
        settings = Mock()
        settings.cleanup_retention_days = 7
        return settings

    def test_deletes_conversations_in_batches(self, mock_settings_30_days):
        """Verify the task deletes conversations using batched deletes."""
        from src.tasks.cleanup_tasks import cleanup_task
        import uuid

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # First call returns IDs, second call returns empty (stop loop)
        conv_ids = [(uuid.uuid4(),) for _ in range(3)]
        conv_batch_result = Mock()
        conv_batch_result.fetchall.return_value = conv_ids

        conv_empty_result = Mock()
        conv_empty_result.fetchall.return_value = []

        exec_empty_result = Mock()
        exec_empty_result.fetchall.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[
                conv_batch_result,  # SELECT conv ids batch 1
                None,               # DELETE conv batch 1
                conv_empty_result,  # SELECT conv ids batch 2 (empty, stop)
                exec_empty_result,  # SELECT exec ids batch 1 (empty, stop)
            ]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 3
        assert result["agent_executions_deleted"] == 0
        # Commit called once per batch
        assert mock_session.commit.call_count >= 1

    def test_deletes_agent_executions_in_batches(self, mock_settings_30_days):
        """Verify the task deletes agent executions using batched deletes."""
        from src.tasks.cleanup_tasks import cleanup_task
        import uuid

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        conv_empty_result = Mock()
        conv_empty_result.fetchall.return_value = []

        exec_ids = [(uuid.uuid4(),) for _ in range(5)]
        exec_batch_result = Mock()
        exec_batch_result.fetchall.return_value = exec_ids

        exec_empty_result = Mock()
        exec_empty_result.fetchall.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[
                conv_empty_result,   # SELECT conv ids (empty)
                exec_batch_result,   # SELECT exec ids batch 1
                None,                # DELETE exec batch 1
                exec_empty_result,   # SELECT exec ids batch 2 (empty, stop)
            ]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 0
        assert result["agent_executions_deleted"] == 5

    def test_respects_retention_days_setting(self, mock_settings_7_days):
        """Verify the task uses the configured retention days."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        empty_result = Mock()
        empty_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=empty_result)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_7_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        # Verify the cutoff date is approximately 7 days ago
        cutoff_date = datetime.fromisoformat(result["cutoff_date"])
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        # Allow 1 minute tolerance for test execution time
        assert abs((cutoff_date - expected_cutoff).total_seconds()) < 60

    def test_handles_zero_records_to_delete(self, mock_settings_30_days):
        """Verify the task handles case with no records to delete."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        empty_result = Mock()
        empty_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=empty_result)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 0
        assert result["agent_executions_deleted"] == 0

    def test_empty_batch_means_no_delete(self, mock_settings_30_days):
        """Verify no DELETE is executed when the SELECT returns empty."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        execute_calls = []

        async def track_execute(query):
            execute_calls.append(query)
            result = Mock()
            result.fetchall.return_value = []
            return result

        mock_session.execute = track_execute

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                cleanup_task()

        # Only 2 SELECT queries (one per model), no DELETE queries
        assert len(execute_calls) == 2

    def test_commits_per_batch(self, mock_settings_30_days):
        """Verify commit is called after each batch deletion."""
        from src.tasks.cleanup_tasks import cleanup_task
        import uuid

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Two batches of conversations
        batch1 = Mock()
        batch1.fetchall.return_value = [(uuid.uuid4(),) for _ in range(3)]

        batch2 = Mock()
        batch2.fetchall.return_value = [(uuid.uuid4(),) for _ in range(2)]

        empty = Mock()
        empty.fetchall.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[
                batch1,  # SELECT conv batch 1
                None,    # DELETE conv batch 1
                batch2,  # SELECT conv batch 2
                None,    # DELETE conv batch 2
                empty,   # SELECT conv batch 3 (empty)
                empty,   # SELECT exec batch 1 (empty)
            ]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 5
        # Commit should be called at least 2 times (once per batch)
        assert mock_session.commit.call_count >= 2
