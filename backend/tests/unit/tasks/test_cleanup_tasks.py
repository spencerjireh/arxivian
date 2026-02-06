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

    def test_deletes_conversations_older_than_retention(self, mock_settings_30_days):
        """Verify the task deletes conversations older than retention period."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock count queries
        conv_count_result = Mock()
        conv_count_result.scalar.return_value = 5

        exec_count_result = Mock()
        exec_count_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(
            side_effect=[conv_count_result, None, exec_count_result, None]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 5
        mock_session.commit.assert_called_once()

    def test_deletes_agent_executions_older_than_retention(self, mock_settings_30_days):
        """Verify the task deletes agent executions older than retention period."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock count queries
        conv_count_result = Mock()
        conv_count_result.scalar.return_value = 0

        exec_count_result = Mock()
        exec_count_result.scalar.return_value = 10

        mock_session.execute = AsyncMock(
            side_effect=[conv_count_result, exec_count_result, None]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["agent_executions_deleted"] == 10
        mock_session.commit.assert_called_once()

    def test_respects_retention_days_setting(self, mock_settings_7_days):
        """Verify the task uses the configured retention days."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Track the queries to verify cutoff date
        executed_queries = []

        async def track_execute(query):
            executed_queries.append(query)
            result = Mock()
            result.scalar.return_value = 0
            return result

        mock_session.execute = track_execute

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

    def test_returns_deletion_counts(self, mock_settings_30_days):
        """Verify the task returns accurate deletion counts."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock count queries
        conv_count_result = Mock()
        conv_count_result.scalar.return_value = 15

        exec_count_result = Mock()
        exec_count_result.scalar.return_value = 25

        mock_session.execute = AsyncMock(
            side_effect=[conv_count_result, None, exec_count_result, None]
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert "conversations_deleted" in result
        assert "agent_executions_deleted" in result
        assert "cutoff_date" in result
        assert result["conversations_deleted"] == 15
        assert result["agent_executions_deleted"] == 25

    def test_commits_changes(self, mock_settings_30_days):
        """Verify the task commits all changes to the database."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock count queries returning 0 (nothing to delete)
        count_result = Mock()
        count_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(return_value=count_result)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                cleanup_task()

        mock_session.commit.assert_called_once()

    def test_handles_zero_records_to_delete(self, mock_settings_30_days):
        """Verify the task handles case with no records to delete."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock count queries returning 0
        count_result = Mock()
        count_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(return_value=count_result)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                result = cleanup_task()

        assert result["conversations_deleted"] == 0
        assert result["agent_executions_deleted"] == 0
        # Should still commit even with no deletions
        mock_session.commit.assert_called_once()

    def test_skips_delete_when_count_is_zero(self, mock_settings_30_days):
        """Verify delete is skipped when count is 0 to avoid unnecessary queries."""
        from src.tasks.cleanup_tasks import cleanup_task

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        execute_call_count = 0

        async def count_execute_calls(query):
            nonlocal execute_call_count
            execute_call_count += 1
            result = Mock()
            result.scalar.return_value = 0
            return result

        mock_session.execute = count_execute_calls

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.cleanup_tasks.get_settings", return_value=mock_settings_30_days):
            with patch("src.tasks.cleanup_tasks.AsyncSessionLocal", mock_session_ctx):
                cleanup_task()

        # Only 2 count queries should execute (not 4 with deletes)
        assert execute_call_count == 2
