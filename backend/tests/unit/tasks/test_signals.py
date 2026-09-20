"""Unit tests for Celery signals."""

from unittest.mock import Mock, patch


class TestWorkerProcessSignals:
    """Tests for worker process init/shutdown signals."""

    def test_process_init_starts_loop_and_tracing(self):
        from src.tasks.signals import _on_worker_process_init

        with (
            patch("src.tasks.signals.start_worker_loop") as mock_start,
            patch("src.tasks.signals.configure_tracing") as mock_tracing,
            patch("src.tasks.signals.logfire") as mock_logfire,
        ):
            _on_worker_process_init()

        mock_start.assert_called_once()
        mock_tracing.assert_called_once_with("arxivian-worker")
        mock_logfire.instrument_celery.assert_called_once()
        mock_logfire.instrument_sqlalchemy.assert_called_once()

    def test_process_shutdown_stops_loop(self):
        from src.tasks.signals import _on_worker_process_shutdown

        with patch("src.tasks.signals.stop_worker_loop") as mock_stop:
            _on_worker_process_shutdown()

        mock_stop.assert_called_once()


class TestWorkerShutdownSignal:
    """Tests for the worker shutdown (tracing flush) signal."""

    def test_flushes_tracing(self):
        from src.tasks.signals import _on_worker_shutdown

        with patch("src.tasks.signals.flush") as mock_flush:
            _on_worker_shutdown()

        mock_flush.assert_called_once()


class TestTaskStatusSignals:
    """Tests for task prerun/success/failure status tracking."""

    def test_prerun_calls_update_with_started(self):
        """Verify task_prerun updates status to started."""
        with patch("src.tasks.signals._update_task_execution_status") as mock_update:
            from src.tasks.signals import _on_task_prerun

            _on_task_prerun(task_id="test-task-123")

        mock_update.assert_called_once_with("test-task-123", "started")

    def test_success_calls_update_with_success(self):
        """Verify task_success updates status to success."""
        with patch("src.tasks.signals._update_task_execution_status") as mock_update:
            from src.tasks.signals import _on_task_success

            mock_sender = Mock()
            mock_sender.request.id = "test-task-456"

            _on_task_success(sender=mock_sender)

        mock_update.assert_called_once_with("test-task-456", "success")

    def test_failure_calls_update_with_failure_and_error(self):
        """Verify task_failure updates status to failure with error message."""
        with patch("src.tasks.signals._update_task_execution_status") as mock_update:
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
            with patch("src.tasks.signals.AsyncSessionLocal", side_effect=Exception("DB error")):
                # Should not raise
                _update_task_execution_status("test-task", "started")

            mock_log.warning.assert_called_once()
