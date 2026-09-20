"""Tracing configuration: safe without a token, idempotent, wired into structlog."""

import logfire
import pytest
import structlog

from src import observability
from src.utils.logger import configure_logging


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
