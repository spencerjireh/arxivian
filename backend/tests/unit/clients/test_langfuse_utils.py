"""Tests for langfuse_utils module."""

from unittest.mock import MagicMock, patch

from src.clients.langfuse_utils import (
    get_trace_context,
    set_trace_context,
    shutdown_langfuse,
)


class TestTraceContext:
    """Tests for trace context get/set."""

    def test_default_context_is_none(self):
        set_trace_context(None)
        assert get_trace_context() is None

    def test_set_and_get_trace_id(self):
        set_trace_context("trace-abc-123")
        assert get_trace_context() == "trace-abc-123"
        set_trace_context(None)  # Clean up

    def test_clear_trace_context(self):
        set_trace_context("trace-xyz")
        set_trace_context(None)
        assert get_trace_context() is None


class TestGetLangfuse:
    """Tests for get_langfuse singleton."""

    def test_returns_none_when_langfuse_not_available(self):
        with patch("src.clients.langfuse_utils.LANGFUSE_AVAILABLE", False):
            from src.clients.langfuse_utils import get_langfuse

            result = get_langfuse()
            assert result is None

    def test_returns_none_when_disabled(self):
        with patch("src.clients.langfuse_utils.LANGFUSE_AVAILABLE", True):
            with patch("src.clients.langfuse_utils._langfuse_client", None):
                mock_settings = MagicMock()
                mock_settings.langfuse_enabled = False
                with patch("src.config.get_settings", return_value=mock_settings):
                    from src.clients.langfuse_utils import get_langfuse

                    result = get_langfuse()
                    assert result is None


class TestShutdownLangfuse:
    """Tests for shutdown_langfuse."""

    def test_shutdown_flushes_and_clears(self):
        import src.clients.langfuse_utils as langfuse_utils

        mock_client = MagicMock()

        with patch("src.clients.langfuse_utils._langfuse_client", mock_client):
            shutdown_langfuse()
            mock_client.flush.assert_called_once()
            mock_client.shutdown.assert_called_once()

        assert langfuse_utils._langfuse_client is None

    def test_shutdown_noop_when_no_client(self):
        import src.clients.langfuse_utils as langfuse_utils

        with patch("src.clients.langfuse_utils._langfuse_client", None):
            # Should not raise
            shutdown_langfuse()

        assert langfuse_utils._langfuse_client is None
