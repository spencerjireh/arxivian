"""Unit tests for Celery signals."""

from unittest.mock import patch


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
