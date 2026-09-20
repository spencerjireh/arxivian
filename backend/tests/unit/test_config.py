"""Unit tests for Settings defaults.

Init kwargs outrank env/.env in pydantic-settings, so these constructions are
deterministic regardless of the ambient env.
"""

from __future__ import annotations

import pytest

from src.config import Settings

_CLERK = "test.clerk.accounts.dev"  # the one required field with no default


@pytest.mark.unit
class TestSettings:
    def test_llm_defaults(self):
        settings = Settings(clerk_domain=_CLERK)
        assert settings.default_llm_model == "openai/gpt-5-nano"
        assert settings.structured_output_model == "openai/gpt-5-nano"
        # Removed in Phase 3: no allowlist, no NIM provider, no checkpointer.
        for gone in ("allowed_llm_models", "nvidia_nim_api_key", "redis_checkpoint_url"):
            assert not hasattr(settings, gone)

    def test_agent_defaults(self):
        settings = Settings(clerk_domain=_CLERK)
        assert settings.guardrail_threshold == 75
        assert settings.max_iterations == 5
        assert settings.conversation_window == 5
        assert settings.default_top_k == 3

    def test_typesafe_defaults(self):
        settings = Settings(clerk_domain=_CLERK)
        assert settings.typesafe_model == "jev-1.13.0"
        assert settings.typesafe_timeout_seconds == 60
        assert settings.arxiv_crawl_pause_seconds == 3
