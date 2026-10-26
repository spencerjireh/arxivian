"""Tests for the construction module."""

from unittest.mock import patch

import pytest

from src.clients.anthropic_client import AnthropicClient
from src.clients.openai_client import OpenAIClient
from src.factories import (
    _build_llm_client,
    get_agent_llm_client,
    get_llm_client,
    get_triage_llm_client,
)


def _make_settings(**overrides):
    defaults = {
        "default_llm_model": "openai/gpt-5-nano",
        "llm_call_timeout_seconds": 30,
        "structured_output_model": None,
        "triage_llm_model": None,
        "agent_llm_model": None,
        "agent_prompt_caching": False,
        "openai_api_key": "oa-key",  # pragma: allowlist secret
        "anthropic_api_key": "an-key",  # pragma: allowlist secret
    }
    defaults.update(overrides)

    class FakeSettings:
        def __getattr__(self, name):
            return defaults[name]

    return FakeSettings()


@pytest.fixture(autouse=True)
def _clear_client_cache():
    """`_build_llm_client` is lru_cached on the model triple, not on the settings it reads.

    That is right in production, where settings are themselves cached and immutable for the
    process, but it means a test patching settings would otherwise be handed a client built
    from an earlier test's settings.
    """
    _build_llm_client.cache_clear()
    yield
    _build_llm_client.cache_clear()


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


@pytest.mark.unit
class TestProviderDispatch:
    """The provider prefix on the model string picks the implementation (ARX-75)."""

    def test_openai_prefix_builds_the_openai_client(self):
        with patch("src.factories.get_settings", return_value=_make_settings()):
            assert isinstance(get_llm_client(), OpenAIClient)

    def test_bare_model_is_treated_as_openai(self):
        settings = _make_settings(default_llm_model="gpt-5-nano")
        with patch("src.factories.get_settings", return_value=settings):
            assert isinstance(get_llm_client(), OpenAIClient)

    def test_anthropic_prefix_builds_the_anthropic_client(self):
        settings = _make_settings(default_llm_model="anthropic/claude-haiku-4-5-20251001")
        with patch("src.factories.get_settings", return_value=settings):
            client = get_llm_client()
        assert isinstance(client, AnthropicClient)
        assert client.provider_name == "anthropic"

    def test_missing_anthropic_key_raises_rather_than_falling_back(self):
        """A silent substitution would change behaviour and cost while everything looked fine."""
        settings = _make_settings(
            default_llm_model="anthropic/claude-haiku-4-5-20251001", anthropic_api_key=""
        )
        with (
            patch("src.factories.get_settings", return_value=settings),
            pytest.raises(ValueError, match="ANTHROPIC_API_KEY"),
        ):
            get_llm_client()

    def test_unknown_provider_raises(self):
        settings = _make_settings(default_llm_model="cohere/command")
        with (
            patch("src.factories.get_settings", return_value=settings),
            pytest.raises(ValueError, match="Unsupported provider"),
        ):
            get_llm_client()


@pytest.mark.unit
class TestPerRoleClients:
    def test_roles_fall_back_to_the_default_model(self):
        """Unset role overrides must leave behaviour exactly as it was."""
        with patch("src.factories.get_settings", return_value=_make_settings()):
            assert get_triage_llm_client().model == "openai/gpt-5-nano"
            assert get_agent_llm_client().model == "openai/gpt-5-nano"

    def test_roles_can_use_different_providers(self):
        settings = _make_settings(
            triage_llm_model="openai/gpt-5-nano",
            agent_llm_model="anthropic/claude-sonnet-5",
        )
        with patch("src.factories.get_settings", return_value=settings):
            assert isinstance(get_triage_llm_client(), OpenAIClient)
            assert isinstance(get_agent_llm_client(), AnthropicClient)

    def test_triage_structured_model_follows_its_role(self):
        """Triage is entirely structured calls, so it must not inherit a foreign one."""
        settings = _make_settings(
            triage_llm_model="openai/gpt-5-nano", structured_output_model="anthropic/x"
        )
        with patch("src.factories.get_settings", return_value=settings):
            assert get_triage_llm_client()._structured_output_model == "openai/gpt-5-nano"

    def test_prompt_caching_only_applies_to_anthropic(self):
        """The flag is meaningless on OpenAI and must not be passed to it."""
        settings = _make_settings(
            agent_llm_model="anthropic/claude-sonnet-5", agent_prompt_caching=True
        )
        with patch("src.factories.get_settings", return_value=settings):
            assert get_agent_llm_client()._cache_system is True

        _build_llm_client.cache_clear()
        settings = _make_settings(agent_llm_model="openai/gpt-5-nano", agent_prompt_caching=True)
        with patch("src.factories.get_settings", return_value=settings):
            assert isinstance(get_agent_llm_client(), OpenAIClient)
