"""Shared pytest fixtures for task unit tests."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from contextlib import asynccontextmanager

from src.schemas.ingest import IngestResponse


@pytest.fixture
def mock_async_session_local():
    """Mock AsyncSessionLocal that yields a mock session."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    @asynccontextmanager
    async def session_context():
        yield mock_session

    return session_context, mock_session


@pytest.fixture
def mock_ingest_service():
    """Mock IngestService with IngestResponse return."""
    service = AsyncMock()
    service.ingest_papers = AsyncMock(
        return_value=IngestResponse(
            status="completed",
            papers_fetched=5,
            papers_processed=5,
            chunks_created=50,
            duration_seconds=10.5,
            errors=[],
        )
    )
    return service


@pytest.fixture
def mock_user_repository():
    """Mock UserRepository with sample users."""
    repo = AsyncMock()
    repo.get_users_with_searches = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def sample_user_with_searches():
    """User with arxiv_searches in preferences."""
    from src.models.user import User

    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_test123"
    user.email = "test@example.com"
    user.preferences = {
        "arxiv_searches": [
            {
                "name": "ML Papers",
                "query": "machine learning",
                "categories": ["cs.LG"],
                "max_results": 10,
                "enabled": True,
            },
            {
                "name": "AI Papers",
                "query": "artificial intelligence",
                "categories": ["cs.AI"],
                "max_results": 5,
                "enabled": True,
            },
        ]
    }
    return user


@pytest.fixture
def sample_user_with_disabled_search():
    """User with a disabled arxiv search."""
    from src.models.user import User

    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_disabled123"
    user.email = "disabled@example.com"
    user.preferences = {
        "arxiv_searches": [
            {
                "name": "Disabled Search",
                "query": "test query",
                "enabled": False,
            }
        ]
    }
    return user


@pytest.fixture
def sample_user_empty_query():
    """User with empty query in arxiv search."""
    from src.models.user import User

    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_empty123"
    user.email = "empty@example.com"
    user.preferences = {
        "arxiv_searches": [
            {
                "name": "Empty Query Search",
                "query": "",
                "enabled": True,
            }
        ]
    }
    return user


@pytest.fixture
def mock_celery_task():
    """Mock Celery task with request context."""
    task = Mock()
    task.request = Mock()
    task.request.id = str(uuid.uuid4())
    task.request.retries = 0
    return task


@pytest.fixture
def mock_settings():
    """Mock settings for tasks."""
    settings = Mock()
    settings.cleanup_retention_days = 30
    settings.report_include_usage = True
    settings.report_include_papers = True
    settings.report_include_health = True
    settings.langfuse_enabled = False
    settings.celery_broker_url = "redis://localhost:6379/0"
    settings.celery_result_backend = "redis://localhost:6379/0"
    settings.celery_task_timeout = 3600
    settings.ingest_schedule_cron = "0 2 * * *"
    settings.report_schedule_cron = "0 8 * * 1"
    settings.cleanup_schedule_cron = "0 3 * * *"
    return settings
