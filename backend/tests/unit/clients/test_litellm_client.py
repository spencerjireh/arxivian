"""Tests for LiteLLMClient."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, ConfigDict

from src.clients.litellm_client import (
    NATIVE_STRUCTURED_OUTPUT_PROVIDERS,
    LiteLLMClient,
    _inject_schema,
    _provider_from_model,
)
from src.exceptions import LLMTimeoutError


class SampleResponse(BaseModel):
    """Sample response model for structured output tests."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    score: int


@pytest.fixture
def client():
    """Create a LiteLLMClient instance."""
    return LiteLLMClient(model="openai/gpt-4o-mini", timeout=30.0)


@pytest.fixture
def nvidia_client():
    """Create a LiteLLMClient for NVIDIA NIM."""
    return LiteLLMClient(model="nvidia_nim/meta/llama-3.1-8b-instruct", timeout=30.0)


@pytest.fixture
def messages():
    """Sample messages list."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]


@pytest.fixture
def structured_response():
    """Mock response for structured output calls."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = '{"answer": "ok", "score": 1}'
    return resp


class TestProviderParsing:
    """Tests for provider name extraction from model string."""

    def test_openai_provider(self, client):
        assert client.provider_name == "openai"

    def test_nvidia_provider(self, nvidia_client):
        assert nvidia_client.provider_name == "nvidia_nim"

    def test_model_without_prefix(self):
        c = LiteLLMClient(model="gpt-4o-mini")
        assert c.provider_name == "openai"

    def test_model_property(self, client):
        assert client.model == "openai/gpt-4o-mini"


class TestGenerateCompletion:
    """Tests for non-streaming completion."""

    @pytest.mark.asyncio
    async def test_completion_returns_content(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello there!"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.generate_completion(messages)

        assert result == "Hello there!"
        mock.assert_called_once()
        call_kwargs = mock.call_args
        assert call_kwargs.kwargs["model"] == "openai/gpt-4o-mini"
        assert call_kwargs.kwargs["temperature"] == 0.3
        assert call_kwargs.kwargs["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_completion_with_model_override(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = None

        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            await client.generate_completion(messages, model="openai/gpt-4o")

        assert mock.call_args.kwargs["model"] == "openai/gpt-4o"

    @pytest.mark.asyncio
    async def test_completion_timeout_raises(self, client, messages):
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = asyncio.TimeoutError()
            with pytest.raises(LLMTimeoutError):
                await client.generate_completion(messages, timeout=1.0)


class TestGenerateStreaming:
    """Tests for streaming completion via generate_stream."""

    @pytest.mark.asyncio
    async def test_streaming_yields_tokens(self, client, messages):
        chunks = []
        for text in ["Hello", " ", "world"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = text
            chunks.append(chunk)

        async def mock_acompletion(**kwargs):
            async def gen():
                for c in chunks:
                    yield c

            return gen()

        with patch("src.clients.litellm_client.litellm.acompletion", side_effect=mock_acompletion):
            tokens = [t async for t in client.generate_stream(messages)]

        assert tokens == ["Hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_streaming_skips_empty_deltas(self, client, messages):
        chunks = []
        for text in ["Hello", None, "world"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = text
            chunks.append(chunk)

        async def mock_acompletion(**kwargs):
            async def gen():
                for c in chunks:
                    yield c

            return gen()

        with patch("src.clients.litellm_client.litellm.acompletion", side_effect=mock_acompletion):
            tokens = [t async for t in client.generate_stream(messages)]

        assert tokens == ["Hello", "world"]

    @pytest.mark.asyncio
    async def test_streaming_timeout_raises(self, client, messages):
        async def mock_acompletion(**kwargs):
            raise asyncio.TimeoutError()

        with patch("src.clients.litellm_client.litellm.acompletion", side_effect=mock_acompletion):
            with pytest.raises(LLMTimeoutError):
                async for _ in client.generate_stream(messages, timeout=1.0):
                    pass


class TestGenerateStructured:
    """Tests for structured output generation."""

    @pytest.mark.asyncio
    async def test_structured_output_parses_model(self, client, messages, structured_response):
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = structured_response
            result = await client.generate_structured(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.answer == "ok"
        assert result.score == 1

    @pytest.mark.asyncio
    async def test_structured_output_empty_content_raises(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            with pytest.raises(ValueError, match="empty content"):
                await client.generate_structured(messages, SampleResponse)

    @pytest.mark.asyncio
    async def test_structured_timeout_raises(self, client, messages):
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.side_effect = asyncio.TimeoutError()
            with pytest.raises(LLMTimeoutError):
                await client.generate_structured(messages, SampleResponse, timeout=1.0)

    @pytest.mark.asyncio
    async def test_native_provider_passes_pydantic_response_format(
        self, client, messages, structured_response
    ):
        """OpenAI (native) should pass the Pydantic class as response_format."""
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = structured_response
            await client.generate_structured(messages, SampleResponse)

        assert mock.call_args.kwargs["response_format"] is SampleResponse

    @pytest.mark.asyncio
    async def test_non_native_provider_uses_json_mode(
        self, nvidia_client, messages, structured_response
    ):
        """NIM (non-native) should use json_object mode with schema in prompt."""
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = structured_response
            await nvidia_client.generate_structured(messages, SampleResponse)

        assert mock.call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_non_native_provider_injects_schema_into_system(
        self, nvidia_client, messages, structured_response
    ):
        """Schema injection should append to existing system message."""
        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = structured_response
            await nvidia_client.generate_structured(messages, SampleResponse)

        sent_messages = mock.call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"
        assert "You are a helpful assistant." in sent_messages[0]["content"]
        assert '"answer"' in sent_messages[0]["content"]
        assert '"score"' in sent_messages[0]["content"]


class TestStructuredModelOverride:
    """Tests for structured output model override."""

    @pytest.mark.asyncio
    async def test_uses_structured_model_override(self, messages, structured_response):
        client = LiteLLMClient(
            model="nvidia_nim/openai/gpt-oss-120b",
            structured_output_model="openai/gpt-4o-mini",
        )
        with patch(
            "src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = structured_response
            await client.generate_structured(messages, SampleResponse)

        # Override to openai -> native path -> Pydantic response_format
        assert mock.call_args.kwargs["model"] == "openai/gpt-4o-mini"
        assert mock.call_args.kwargs["response_format"] is SampleResponse

    @pytest.mark.asyncio
    async def test_explicit_model_param_overrides_structured_model(
        self, messages, structured_response
    ):
        client = LiteLLMClient(
            model="nvidia_nim/openai/gpt-oss-120b",
            structured_output_model="openai/gpt-4o-mini",
        )
        with patch(
            "src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = structured_response
            await client.generate_structured(messages, SampleResponse, model="openai/gpt-4o")

        assert mock.call_args.kwargs["model"] == "openai/gpt-4o"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_model_without_override(
        self, messages, structured_response
    ):
        client = LiteLLMClient(model="nvidia_nim/openai/gpt-oss-120b")
        with patch(
            "src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = structured_response
            await client.generate_structured(messages, SampleResponse)

        assert mock.call_args.kwargs["model"] == "nvidia_nim/openai/gpt-oss-120b"
        # Non-native -> json_object mode
        assert mock.call_args.kwargs["response_format"] == {"type": "json_object"}


class TestProviderFromModel:
    """Tests for _provider_from_model helper."""

    def test_prefixed_model(self):
        assert _provider_from_model("nvidia_nim/openai/gpt-oss-120b") == "nvidia_nim"

    def test_openai_prefixed(self):
        assert _provider_from_model("openai/gpt-4o-mini") == "openai"

    def test_unprefixed_defaults_to_openai(self):
        assert _provider_from_model("gpt-4o-mini") == "openai"

    def test_anthropic(self):
        assert _provider_from_model("anthropic/claude-3-opus") == "anthropic"

    def test_google(self):
        assert _provider_from_model("google/gemini-pro") == "google"


class TestInjectSchema:
    """Tests for _inject_schema helper."""

    def test_appends_schema_to_system_message(self):
        msgs: list = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hi"},
        ]
        result = _inject_schema(msgs, SampleResponse)
        assert result[0]["role"] == "system"
        assert result[0]["content"].startswith("Be helpful.")
        assert '"answer"' in result[0]["content"]
        assert result[1] == {"role": "user", "content": "Hi"}

    def test_does_not_mutate_original(self):
        msgs: list = [
            {"role": "system", "content": "Original."},
            {"role": "user", "content": "Hi"},
        ]
        _inject_schema(msgs, SampleResponse)
        assert msgs[0]["content"] == "Original."

    def test_creates_system_message_when_missing(self):
        msgs: list = [{"role": "user", "content": "Hi"}]
        result = _inject_schema(msgs, SampleResponse)
        assert result[0]["role"] == "system"
        assert '"answer"' in result[0]["content"]
        assert result[1] == {"role": "user", "content": "Hi"}

    def test_only_injects_into_first_system_message(self):
        msgs: list = [
            {"role": "system", "content": "First."},
            {"role": "system", "content": "Second."},
            {"role": "user", "content": "Hi"},
        ]
        result = _inject_schema(msgs, SampleResponse)
        assert '"answer"' in result[0]["content"]
        assert '"answer"' not in result[1]["content"]


class TestNativeProviderWhitelist:
    """Tests for the NATIVE_STRUCTURED_OUTPUT_PROVIDERS constant."""

    def test_openai_is_native(self):
        assert "openai" in NATIVE_STRUCTURED_OUTPUT_PROVIDERS

    def test_anthropic_is_native(self):
        assert "anthropic" in NATIVE_STRUCTURED_OUTPUT_PROVIDERS

    def test_google_is_native(self):
        assert "google" in NATIVE_STRUCTURED_OUTPUT_PROVIDERS

    def test_nvidia_nim_is_not_native(self):
        assert "nvidia_nim" not in NATIVE_STRUCTURED_OUTPUT_PROVIDERS


class TestMetadata:
    """Tests for trace context metadata."""

    @pytest.mark.asyncio
    async def test_metadata_includes_trace_id(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_response.usage = None

        with patch("src.clients.litellm_client.get_trace_context", return_value="trace-123"):
            with patch(
                "src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock
            ) as mock:
                mock.return_value = mock_response
                await client.generate_completion(messages)

            metadata = mock.call_args.kwargs.get("metadata", {})
            assert metadata.get("existing_trace_id") == "trace-123"

    @pytest.mark.asyncio
    async def test_metadata_empty_without_trace(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_response.usage = None

        with patch("src.clients.litellm_client.get_trace_context", return_value=None):
            with patch(
                "src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock
            ) as mock:
                mock.return_value = mock_response
                await client.generate_completion(messages)

            metadata = mock.call_args.kwargs.get("metadata", {})
            assert "existing_trace_id" not in metadata
