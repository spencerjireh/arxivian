"""Shared pytest fixtures."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.services.agent_service.context import ConversationFormatter, AgentContext


@pytest.fixture
def conversation_formatter():
    """Create a ConversationFormatter instance."""
    return ConversationFormatter(max_turns=5)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.provider_name = "mock"
    client.model = "mock-model"
    return client


@pytest.fixture
def mock_search_service():
    """Create a mock search service."""
    return AsyncMock()


@pytest.fixture
def mock_context(mock_llm_client, mock_search_service, conversation_formatter):
    """Create a mock AgentContext."""
    ctx = Mock(spec=AgentContext)
    ctx.llm_client = mock_llm_client
    ctx.search_service = mock_search_service
    ctx.conversation_formatter = conversation_formatter
    ctx.guardrail_threshold = 75
    ctx.top_k = 3
    ctx.max_retrieval_attempts = 3
    ctx.max_iterations = 5
    ctx.temperature = 0.3
    return ctx
