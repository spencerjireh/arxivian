"""Unit tests for scheduled background tasks."""

from unittest.mock import patch, Mock, AsyncMock
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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        # Should queue 2 tasks (one for each search in user's preferences)
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 2
        assert len(result["tasks"]) == 2

        # Verify apply_async was called with correct kwargs
        calls = mock_apply_async.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["kwargs"]["query"] == "machine learning"
        assert calls[0].kwargs["kwargs"]["categories"] == ["cs.LG"]
        assert calls[0].kwargs["kwargs"]["max_results"] == 10

        assert calls[1].kwargs["kwargs"]["query"] == "artificial intelligence"
        assert calls[1].kwargs["kwargs"]["categories"] == ["cs.AI"]
        assert calls[1].kwargs["kwargs"]["max_results"] == 5

    def test_uses_staggered_countdown(self, sample_user_with_searches):
        """Verify tasks are staggered with countdown values."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    daily_ingest_task()

        # Verify countdown values: 0, 30
        calls = mock_apply_async.call_args_list
        assert calls[0].kwargs["countdown"] == 0
        assert calls[1].kwargs["countdown"] == 30

    def test_uses_deterministic_task_ids(self, sample_user_with_searches):
        """Verify deterministic task IDs are generated."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    daily_ingest_task()

        # Verify task_id kwarg is present (deterministic)
        calls = mock_apply_async.call_args_list
        for call in calls:
            assert "task_id" in call.kwargs
            assert len(call.kwargs["task_id"]) == 32  # SHA-256 truncated

    def test_returns_spread_duration_minutes(self, sample_user_with_searches):
        """Verify spread_duration_minutes is in the result."""
        from src.tasks.scheduled_tasks import daily_ingest_task

        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.get_users_with_searches = AsyncMock(
            return_value=[sample_user_with_searches]
        )

        mock_task = Mock()
        mock_task.id = "queued-task-id"
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        assert "spread_duration_minutes" in result
        # 2 tasks, staggered by 30s: (2-1) * 30 / 60 = 0.5 minutes
        assert result["spread_duration_minutes"] == 0.5

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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        # No tasks should be queued
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 0
        assert len(result["tasks"]) == 0
        mock_apply_async.assert_not_called()

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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        # No tasks should be queued
        assert result["status"] == "completed"
        assert result["tasks_queued"] == 0
        mock_apply_async.assert_not_called()

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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        # Check result structure
        assert "status" in result
        assert "tasks_queued" in result
        assert "tasks" in result
        assert "spread_duration_minutes" in result

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
        mock_ingest_task.apply_async.assert_not_called()

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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    result = daily_ingest_task()

        # Should queue 3 tasks (2 from first user + 1 from second)
        assert result["tasks_queued"] == 3
        assert len(result["tasks"]) == 3

        # Verify countdown stagger: 0, 30, 60
        calls = mock_apply_async.call_args_list
        assert calls[0].kwargs["countdown"] == 0
        assert calls[1].kwargs["countdown"] == 30
        assert calls[2].kwargs["countdown"] == 60

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
        mock_apply_async = Mock(return_value=mock_task)

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
                    mock_ingest_task.apply_async = mock_apply_async

                    daily_ingest_task()

        # Verify default max_results was used
        call_args = mock_apply_async.call_args
        assert call_args.kwargs["kwargs"]["max_results"] == 10
