"""Tracing configuration: safe without a token, idempotent, wired into structlog."""

import logfire
import pytest
import structlog
from opentelemetry.sdk.trace import TracerProvider

from src import observability
from src.utils.logger import add_trace_id, configure_logging


@pytest.mark.unit
class TestConfigureTracing:
    def test_no_token_means_nothing_is_exported(self, monkeypatch):
        monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
        observability._configured = False

        observability.configure_tracing("arxivian-test")

        config = logfire.DEFAULT_LOGFIRE_INSTANCE.config
        # "if-token-present" with no token resolves to no exporter at configure time.
        assert config.send_to_logfire == "if-token-present"
        assert config.token is None
        assert config.service_name == "arxivian-test"

    def test_idempotent(self, monkeypatch):
        monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
        observability._configured = False
        observability.configure_tracing("first")
        observability.configure_tracing("second")
        assert logfire.DEFAULT_LOGFIRE_INSTANCE.config.service_name == "first"

    def test_flush_is_safe(self):
        observability.flush()

    def test_structlog_chain_includes_logfire_processor(self):
        configure_logging("INFO")
        processors = structlog.get_config()["processors"]
        assert any(isinstance(p, logfire.StructlogProcessor) for p in processors)

    def test_structlog_chain_includes_trace_id_processor(self):
        configure_logging("INFO")
        assert add_trace_id in structlog.get_config()["processors"]


@pytest.mark.unit
class TestTraceId:
    """The Tempo -> Loki jump is a substring match on the raw line, so the id must be in it."""

    def test_none_outside_a_span(self):
        assert observability.current_trace_id() is None

    def test_thirty_two_hex_chars_inside_a_span(self):
        # A provider of its own: the result must not depend on configure_tracing having run.
        with TracerProvider().get_tracer("test").start_as_current_span("t"):
            trace_id = observability.current_trace_id()
        assert trace_id is not None
        assert len(trace_id) == 32
        int(trace_id, 16)  # hex, unprefixed

    def test_processor_omits_the_key_outside_a_span(self):
        assert add_trace_id(None, "info", {}) == {}

    def test_processor_adds_the_key_inside_a_span(self):
        with TracerProvider().get_tracer("test").start_as_current_span("t"):
            event = add_trace_id(None, "info", {"event": "hello"})
        assert event["event"] == "hello"
        assert len(event["trace_id"]) == 32
