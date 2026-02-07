"""Unit tests for ingest background tasks."""

import uuid
import pytest
from unittest.mock import patch, Mock, AsyncMock
from contextlib import asynccontextmanager, contextmanager

from src.schemas.ingest import IngestResponse


@contextmanager
def task_context(task, task_id="test-task-id", retries=0):
    """Context manager to set up Celery task request context."""
    # Push a mock request onto the task's request stack
    task.push_request(id=task_id, retries=retries)
    try:
        yield
    finally:
        task.pop_request()


class TestIngestPapersTask:
    """Tests for the ingest_papers_task Celery task."""

    @pytest.fixture
    def mock_ingest_response(self):
        """Standard successful ingest response."""
        return IngestResponse(
            status="completed",
            papers_fetched=5,
            papers_processed=5,
            chunks_created=50,
            duration_seconds=10.5,
            errors=[],
        )

    def test_ingest_task_calls_service_with_correct_params(
        self, mock_ingest_response
    ):
        """Verify the task calls IngestService with all provided parameters."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    # Use push_request to set up task context
                    with task_context(ingest_papers_task, "test-task-id-123"):
                        result = ingest_papers_task._orig_run(
                            query="machine learning",
                            max_results=20,
                            categories=["cs.LG", "cs.AI"],
                            start_date="2024-01-01",
                            end_date="2024-12-31",
                            force_reprocess=True,
                        )

        # Verify service was called
        mock_service.ingest_papers.assert_called_once()
        call_args = mock_service.ingest_papers.call_args[0][0]
        assert call_args.query == "machine learning"
        assert call_args.max_results == 20
        assert call_args.categories == ["cs.LG", "cs.AI"]
        assert call_args.start_date == "2024-01-01"
        assert call_args.end_date == "2024-12-31"
        assert call_args.force_reprocess is True

    def test_ingest_task_returns_serializable_result(
        self, mock_ingest_response
    ):
        """Verify the task returns a JSON-serializable dictionary."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task):
                        result = ingest_papers_task._orig_run(
                            query="test",
                            max_results=10,
                        )

        # Verify result is a dictionary
        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert result["papers_processed"] == 5
        assert result["chunks_created"] == 50

    def test_ingest_task_commits_session_on_success(
        self, mock_ingest_response
    ):
        """Verify the task commits the database session on success."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task):
                        ingest_papers_task._orig_run(
                            query="test",
                            max_results=10,
                        )

        mock_session.commit.assert_called_once()

    def test_ingest_task_has_correct_retry_config(self):
        """Verify the task has expected retry configuration."""
        from src.tasks.ingest_tasks import ingest_papers_task

        # Check task configuration
        assert ingest_papers_task.max_retries == 3
        assert ingest_papers_task.autoretry_for == (Exception,)
        # retry_backoff and retry_jitter are set
        assert hasattr(ingest_papers_task, "retry_backoff")

    def test_ingest_task_raises_exception_on_failure(self):
        """Verify the task raises exception on service failure (for retry)."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(
            side_effect=Exception("Service failure")
        )

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task):
                        with pytest.raises(Exception) as exc_info:
                            ingest_papers_task._orig_run(
                                query="test",
                                max_results=10,
                            )

        assert "Service failure" in str(exc_info.value)

    def test_ingest_task_creates_trace_when_langfuse_enabled(
        self, mock_ingest_response
    ):
        """Verify the task creates Langfuse trace when enabled."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        mock_trace_obj = Mock()
        mock_trace_obj.update = Mock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace_ctx:
                    mock_trace_ctx.return_value.__enter__ = Mock(
                        return_value=mock_trace_obj
                    )
                    mock_trace_ctx.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task, "traced-task-id"):
                        result = ingest_papers_task._orig_run(
                            query="test",
                            max_results=10,
                        )

                    # Verify trace_task was called with correct params
                    mock_trace_ctx.assert_called_once_with(
                        "ingest_papers",
                        "traced-task-id",
                        {
                            "query": "test",
                            "max_results": 10,
                            "categories": None,
                            "attempt": 1,
                        },
                    )

    def test_ingest_task_works_without_langfuse(
        self, mock_ingest_response
    ):
        """Verify the task works when trace returns None (Langfuse disabled)."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    # Return None for trace (Langfuse disabled)
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task):
                        result = ingest_papers_task._orig_run(
                            query="test",
                            max_results=10,
                        )

        # Should complete successfully even without trace
        assert result["status"] == "completed"

    def test_ingest_task_uses_default_values(
        self, mock_ingest_response
    ):
        """Verify the task uses default values for optional parameters."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    from src.tasks.ingest_tasks import ingest_papers_task

                    with task_context(ingest_papers_task):
                        # Call with only required params, using defaults for rest
                        result = ingest_papers_task._orig_run(
                            query="test",
                        )

        # Verify default values were used
        call_args = mock_service.ingest_papers.call_args[0][0]
        assert call_args.max_results == 10
        assert call_args.categories is None
        assert call_args.start_date is None
        assert call_args.end_date is None
        assert call_args.force_reprocess is False


class TestPersistReport:
    """Tests for report persistence in ingest_papers_task."""

    @pytest.fixture
    def mock_ingest_response(self):
        """Standard successful ingest response."""
        return IngestResponse(
            status="completed",
            papers_fetched=5,
            papers_processed=5,
            chunks_created=50,
            duration_seconds=10.5,
            errors=[],
        )

    def test_persist_report_called_when_user_id_and_search_name(
        self, mock_ingest_response
    ):
        """Verify _persist_report is called when both user_id and search_name are provided."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    with patch(
                        "src.tasks.ingest_tasks._persist_report"
                    ) as mock_persist:
                        from src.tasks.ingest_tasks import ingest_papers_task

                        user_id = str(uuid.uuid4())
                        with task_context(ingest_papers_task):
                            ingest_papers_task._orig_run(
                                query="machine learning",
                                max_results=10,
                                user_id=user_id,
                                search_name="ML Papers",
                            )

                        mock_persist.assert_called_once()
                        call_args = mock_persist.call_args
                        assert call_args[0][0] == user_id
                        assert call_args[0][1] == "ML Papers"
                        assert call_args[0][2] == "machine learning"

    def test_persist_report_not_called_without_user_id(
        self, mock_ingest_response
    ):
        """Verify _persist_report is not called when user_id is not provided."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    with patch(
                        "src.tasks.ingest_tasks._persist_report"
                    ) as mock_persist:
                        from src.tasks.ingest_tasks import ingest_papers_task

                        with task_context(ingest_papers_task):
                            ingest_papers_task._orig_run(
                                query="machine learning",
                                max_results=10,
                            )

                        mock_persist.assert_not_called()

    def test_persist_report_failure_does_not_fail_task(
        self, mock_ingest_response
    ):
        """Verify that _persist_report failure does not cause the task to fail."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_service = AsyncMock()
        mock_service.ingest_papers = AsyncMock(return_value=mock_ingest_response)

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        with patch("src.tasks.ingest_tasks.AsyncSessionLocal", mock_session_ctx):
            with patch(
                "src.tasks.ingest_tasks.get_ingest_service", return_value=mock_service
            ):
                with patch("src.tasks.ingest_tasks.trace_task") as mock_trace:
                    mock_trace.return_value.__enter__ = Mock(return_value=None)
                    mock_trace.return_value.__exit__ = Mock(return_value=False)

                    with patch(
                        "src.tasks.ingest_tasks._persist_report",
                        side_effect=Exception("DB connection failed"),
                    ):
                        from src.tasks.ingest_tasks import ingest_papers_task

                        with task_context(ingest_papers_task):
                            result = ingest_papers_task._orig_run(
                                query="machine learning",
                                max_results=10,
                                user_id=str(uuid.uuid4()),
                                search_name="ML Papers",
                            )

        assert result["status"] == "completed"
        assert result["papers_processed"] == 5
