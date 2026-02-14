"""Tests for client factory functions."""

from unittest.mock import patch

import pytest

from src.exceptions import InvalidModelError
from src.factories.client_factories import get_llm_client


def _make_settings(**overrides):
    """Build a fake settings object with sensible defaults."""
    defaults = {
        "default_llm_model": "openai/gpt-4o-mini",
        "allowed_llm_models": "openai/gpt-4o-mini,openai/gpt-4o",
        "llm_call_timeout_seconds": 30,
        "structured_output_model": None,
    }
    defaults.update(overrides)

    class FakeSettings:
        def __getattr__(self, name):
            return defaults[name]

        def get_allowed_models_list(self):
            return [m.strip() for m in defaults["allowed_llm_models"].split(",") if m.strip()]

        def is_model_allowed(self, model):
            return model in self.get_allowed_models_list()

    return FakeSettings()


class TestGetLlmClientStructuredModel:
    """Tests for structured_output_model wiring in get_llm_client."""

    def test_structured_output_model_wired_to_client(self):
        settings = _make_settings(structured_output_model="openai/gpt-4o")

        with patch("src.factories.client_factories.get_settings", return_value=settings):
            client = get_llm_client()

        assert client._structured_output_model == "openai/gpt-4o"

    def test_no_structured_model_when_empty(self):
        settings = _make_settings(structured_output_model="")

        with patch("src.factories.client_factories.get_settings", return_value=settings):
            client = get_llm_client()

        assert client._structured_output_model is None

    def test_invalid_structured_output_model_raises(self):
        settings = _make_settings(structured_output_model="anthropic/claude-3-opus")

        with patch("src.factories.client_factories.get_settings", return_value=settings):
            with pytest.raises(InvalidModelError):
                get_llm_client()
