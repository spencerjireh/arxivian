"""Shared pytest fixtures for repository tests."""

import pytest
from unittest.mock import AsyncMock, Mock
from contextlib import asynccontextmanager


@pytest.fixture
def mock_async_session():
    """Create a mock AsyncSession for repository tests."""
    session = AsyncMock()

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

    @asynccontextmanager
    async def begin_nested():
        yield

    session.begin_nested = begin_nested

    return session
