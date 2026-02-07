"""Tests for LiteLLMClient."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.clients.litellm_client import LiteLLMClient
from src.exceptions import LLMTimeoutError


class SampleResponse(BaseModel):
    """Sample response model for structured output tests."""

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
    async def test_structured_output_parses_model(self, client, messages):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"answer": "42", "score": 95}'

        with patch("src.clients.litellm_client.litellm.acompletion", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response
            result = await client.generate_structured(messages, SampleResponse)

        assert isinstance(result, SampleResponse)
        assert result.answer == "42"
        assert result.score == 95

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
