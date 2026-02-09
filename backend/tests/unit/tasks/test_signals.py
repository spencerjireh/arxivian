"""Unit tests for Celery signals."""

import asyncio
from unittest.mock import patch, Mock


class TestWorkerLifecycleSignals:
    """Tests for worker process init/shutdown signals."""

    def test_worker_process_init_creates_loop(self):
        """Verify worker_process_init creates a persistent event loop."""
        import src.tasks.signals as signals

        # Reset state
        signals._worker_loop = None
        signals._worker_loop_thread = None

        signals._on_worker_process_init()

        assert signals._worker_loop is not None
        assert not signals._worker_loop.is_closed()
        assert signals._worker_loop_thread is not None
        assert signals._worker_loop_thread.is_alive()

        # Cleanup
        signals._on_worker_process_shutdown()

    def test_worker_process_shutdown_closes_loop(self):
        """Verify worker_process_shutdown closes the event loop."""
        import src.tasks.signals as signals

        # Set up a loop first
        signals._worker_loop = None
        signals._worker_loop_thread = None
        signals._on_worker_process_init()

        loop = signals._worker_loop
        assert loop is not None

        signals._on_worker_process_shutdown()

        assert signals._worker_loop is None
        assert signals._worker_loop_thread is None
        assert loop.is_closed()

    def test_get_worker_loop_returns_loop_when_available(self):
        """Verify get_worker_loop returns the loop when it exists."""
        import src.tasks.signals as signals

        signals._worker_loop = None
        signals._worker_loop_thread = None
        signals._on_worker_process_init()

        loop = signals.get_worker_loop()
        assert loop is not None
        assert not loop.is_closed()

        # Cleanup
        signals._on_worker_process_shutdown()

    def test_get_worker_loop_returns_none_when_not_initialized(self):
        """Verify get_worker_loop returns None before initialization."""
        import src.tasks.signals as signals

        signals._worker_loop = None
        assert signals.get_worker_loop() is None

    def test_get_worker_loop_returns_none_when_closed(self):
        """Verify get_worker_loop returns None when loop is closed."""
        import src.tasks.signals as signals

        loop = asyncio.new_event_loop()
        loop.close()
        signals._worker_loop = loop

        assert signals.get_worker_loop() is None

        # Reset
        signals._worker_loop = None


class TestWorkerShutdownSignal:
    """Tests for worker shutdown (Langfuse) signal."""

    def test_calls_shutdown_task_langfuse(self):
        """Verify worker_shutdown calls shutdown_task_langfuse."""
        from src.tasks.signals import _on_worker_shutdown

        with patch("src.tasks.tracing.shutdown_task_langfuse") as mock_shutdown:
            _on_worker_shutdown()

        mock_shutdown.assert_called_once()


class TestTaskStatusSignals:
    """Tests for task prerun/success/failure status tracking."""

    def test_prerun_calls_update_with_started(self):
        """Verify task_prerun updates status to started."""
        with patch(
            "src.tasks.signals._update_task_execution_status"
        ) as mock_update:
            from src.tasks.signals import _on_task_prerun

            _on_task_prerun(task_id="test-task-123")

        mock_update.assert_called_once_with("test-task-123", "started")

    def test_success_calls_update_with_success(self):
        """Verify task_success updates status to success."""
        with patch(
            "src.tasks.signals._update_task_execution_status"
        ) as mock_update:
            from src.tasks.signals import _on_task_success

            mock_sender = Mock()
            mock_sender.request.id = "test-task-456"

            _on_task_success(sender=mock_sender)

        mock_update.assert_called_once_with("test-task-456", "success")

    def test_failure_calls_update_with_failure_and_error(self):
        """Verify task_failure updates status to failure with error message."""
        with patch(
            "src.tasks.signals._update_task_execution_status"
        ) as mock_update:
            from src.tasks.signals import _on_task_failure

            exc = ValueError("something went wrong")
            _on_task_failure(task_id="test-task-789", exception=exc)

        mock_update.assert_called_once_with(
            "test-task-789", "failure", error_message="something went wrong"
        )

    def test_db_errors_do_not_propagate(self):
        """Verify DB errors in status update are caught and logged."""
        from src.tasks.signals import _update_task_execution_status

        with patch("src.tasks.signals.log") as mock_log:
            with patch("src.database.AsyncSessionLocal", side_effect=Exception("DB error")):
                # Should not raise
                _update_task_execution_status("test-task", "started")

            mock_log.warning.assert_called_once()
