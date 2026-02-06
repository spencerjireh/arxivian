"""Unit tests for scheduled background tasks."""

import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from contextlib import asynccontextmanager


class TestDailyIngestTask:
    """Tests for the daily_ingest_task."""

    def test_queues_tasks_for_users_with_searches(
        self, sample_user_with_searches
    ):
        """Verify the task queues ingest tasks for each enabled search."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # Should queue 2 tasks (one for each search in user's preferences)
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 2
        assert len(result["tasks"]) == 2

        # Verify the correct queries were passed
        calls = mock_task_delay.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["query"] == "machine learning"
        assert calls[0].kwargs["categories"] == ["cs.LG"]
        assert calls[0].kwargs["max_results"] == 10

        assert calls[1].kwargs["query"] == "artificial intelligence"
        assert calls[1].kwargs["categories"] == ["cs.AI"]
        assert calls[1].kwargs["max_results"] == 5

    def test_skips_disabled_searches(self, sample_user_with_disabled_search):
        """Verify the task skips disabled searches."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_disabled_search]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # No tasks should be queued
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 0
        assert len(result["tasks"]) == 0
        mock_task_delay.assert_not_called()

    def test_skips_searches_without_query(self, sample_user_empty_query):
        """Verify the task skips searches with empty query."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_empty_query]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # No tasks should be queued
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 0
        mock_task_delay.assert_not_called()

    def test_returns_summary_with_queued_count(self, sample_user_with_searches):
        """Verify the task returns a summary with the correct queued count."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # Check result structure
        assert "status" in result
        assert "tasks_queued" in result
        assert "tasks" in result

        # Check task details are captured
        for task_info in result["tasks"]:
            assert "task_id" in task_info
            assert "user_id" in task_info
            assert "search_name" in task_info
            assert "query" in task_info

    def test_handles_empty_user_list(self):
        """Verify the task handles case with no users with searches."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(return_value=[])

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    result = daily_ingest_task()

        # Should complete with zero tasks
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 0
        assert result["tasks"] == []
        mock_ingest_task.delay.assert_not_called()

    def test_handles_multiple_users(self, sample_user_with_searches):
        """Verify the task processes multiple users correctly."""
        from src.tasks.scheduled_tasks import daily_ingest_task
        from src.models.user import User
        import uuid

        # Create a second user
        user2 = Mock(spec=User)
        user2.id = uuid.uuid4()
        user2.clerk_id = "user_second123"
        user2.email = "second@example.com"
        user2.preferences = {
            "arxiv_searches": [
                {
                    "name": "NLP Papers",
                    "query": "natural language processing",
                    "categories": ["cs.CL"],
                    "max_results": 15,
                    "enabled": True,
                }
            ]
        }

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches, user2]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # Should queue 3 tasks (2 from first user + 1 from second)
        assert result["tasks_queued"] == 3
        assert len(result["tasks"]) == 3

    def test_uses_default_max_results_when_not_specified(self):
        """Verify the task uses default max_results of 10 when not specified."""
        from src.tasks.scheduled_tasks import daily_ingest_task
        from src.models.user import User
        import uuid

        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.clerk_id = "user_no_max123"
        user.email = "nomax@example.com"
        user.preferences = {
            "arxiv_searches": [
                {
                    "name": "Simple Search",
                    "query": "deep learning",
                    "enabled": True,
                    # No max_results specified
                }
            ]
        }

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(return_value=[user])

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_task_delay = Mock(return_value=mock_task)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.scheduled_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.scheduled_tasks.UserRepository", return_value=mock_repo
            ):
                with patch(
                    "src.tasks.scheduled_tasks.ingest_papers_task"
                ) as mock_ingest_task:
                    mock_ingest_task.delay = mock_task_delay

                    result = daily_ingest_task()

        # Verify default max_results was used
        call_args = mock_task_delay.call_args
        assert call_args.kwargs["max_results"] == 10
