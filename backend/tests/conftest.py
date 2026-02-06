"""Shared pytest fixtures."""

# Clear settings cache before any imports to prevent stale values with coverage
from src.config import get_settings

get_settings.cache_clear()

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, MagicMock
from contextlib import asynccontextmanager
from datetime import datetime, timezone

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


# Database mocking fixtures


@pytest.fixture
def mock_async_session():
    """Create a mock AsyncSession for repository tests."""
    session = AsyncMock()

    # Mock result object for execute
    mock_result = Mock()
    mock_result.scalar_one_or_none = Mock(return_value=None)
    mock_result.scalar_one = Mock(return_value=0)
    mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
    mock_result.fetchall = Mock(return_value=[])
    mock_result.rowcount = 0

    session.execute = AsyncMock(return_value=mock_result)
    session.scalar = AsyncMock(return_value=0)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.add_all = Mock()
    session.delete = AsyncMock()
    session.expire_all = Mock()

    # Mock begin_nested for savepoint tests
    @asynccontextmanager
    async def begin_nested():
        yield

    session.begin_nested = begin_nested

    return session


@pytest.fixture
def sample_uuid():
    """Return a sample UUID string."""
    return str(uuid.uuid4())
