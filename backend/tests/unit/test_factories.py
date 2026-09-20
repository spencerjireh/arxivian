"""Tests for the construction module."""

from unittest.mock import patch

import pytest

from src.factories import get_llm_client


def _make_settings(**overrides):
    defaults = {
        "default_llm_model": "openai/gpt-5-nano",
        "llm_call_timeout_seconds": 30,
        "structured_output_model": None,
    }
    defaults.update(overrides)

    class FakeSettings:
        def __getattr__(self, name):
            return defaults[name]

    return FakeSettings()


@pytest.mark.unit
class TestGetLlmClient:
    def test_uses_default_model_and_timeout(self):
        with patch("src.factories.get_settings", return_value=_make_settings()):
            client = get_llm_client()
        assert client.model == "openai/gpt-5-nano"
        assert client.default_timeout == 30.0

    def test_structured_output_model_wired_to_client(self):
        settings = _make_settings(structured_output_model="openai/gpt-5")
        with patch("src.factories.get_settings", return_value=settings):
            client = get_llm_client()
        assert client._structured_output_model == "openai/gpt-5"

    def test_no_structured_model_when_empty(self):
        settings = _make_settings(structured_output_model="")
        with patch("src.factories.get_settings", return_value=settings):
            client = get_llm_client()
        assert client._structured_output_model is None
