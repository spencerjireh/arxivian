"""Unit tests for the Settings model-allowlist guard (SPE-282).

The guard fails fast at construction if `default_llm_model` / `scoring_strong_model` (and
`structured_output_model` when set) are not all in `ALLOWED_LLM_MODELS`, instead of crashing
later with an `InvalidModelError` deep in a Celery task. Init kwargs outrank env/.env in
pydantic-settings, so these constructions are deterministic regardless of the ambient env.
"""

from __future__ import annotations

import pytest

from src.config import Settings

_CLERK = "test.clerk.accounts.dev"  # the one required field with no default


def _settings(**overrides) -> Settings:
    return Settings(clerk_domain=_CLERK, **overrides)


class TestModelAllowlistGuard:
    def test_raises_when_scoring_model_not_allowed(self):
        with pytest.raises(RuntimeError) as exc:
            _settings(
                allowed_llm_models="openai/gpt-4o-mini",
                default_llm_model="openai/gpt-4o-mini",
                structured_output_model=None,
                scoring_strong_model="openai/gpt-5-nano",
            )
        message = str(exc.value)
        assert "scoring_strong_model" in message
        assert "ALLOWED_LLM_MODELS" in message

    def test_raises_when_default_model_not_allowed(self):
        with pytest.raises(RuntimeError):
            _settings(
                allowed_llm_models="openai/gpt-4o-mini",
                default_llm_model="openai/gpt-5-nano",
                structured_output_model=None,
                scoring_strong_model="openai/gpt-4o-mini",
            )

    def test_passes_when_all_referenced_models_allowed(self):
        settings = _settings(
            allowed_llm_models="openai/gpt-5-nano,openai/gpt-4o-mini",
            default_llm_model="openai/gpt-5-nano",
            structured_output_model="openai/gpt-5-nano",
            scoring_strong_model="openai/gpt-5-nano",
        )
        assert settings.default_llm_model == "openai/gpt-5-nano"

    def test_empty_structured_model_is_skipped(self):
        # Empty structured_output_model means "use the default" -- must not fail the guard,
        # matching get_llm_client's `structured_output_model or None`.
        settings = _settings(
            allowed_llm_models="openai/gpt-4o-mini",
            default_llm_model="openai/gpt-4o-mini",
            structured_output_model="",
            scoring_strong_model="openai/gpt-4o-mini",
        )
        assert settings.structured_output_model == ""

    def test_set_but_disallowed_structured_model_raises(self):
        with pytest.raises(RuntimeError):
            _settings(
                allowed_llm_models="openai/gpt-4o-mini",
                default_llm_model="openai/gpt-4o-mini",
                structured_output_model="openai/gpt-5-nano",
                scoring_strong_model="openai/gpt-4o-mini",
            )
