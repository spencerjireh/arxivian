"""Shared pytest fixtures for router integration tests."""

import pytest
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


# Mock database before importing app to avoid connection issues
@pytest.fixture(autouse=True)
def mock_database_init():
    """Mock database initialization for all router tests."""
    with patch("src.database.init_db", new_callable=AsyncMock):
        with patch("src.database.engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            yield


@pytest.fixture
def mock_db_session():
    """Create a mock AsyncSession for router tests."""
    session = AsyncMock(spec=AsyncSession)

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
    session.close = AsyncMock()

    @asynccontextmanager
    async def begin_nested():
        yield

    session.begin_nested = begin_nested

    return session


@pytest.fixture
def mock_paper_repo():
    """Create a mock PaperRepository."""
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=([], 0))
    repo.get_by_arxiv_id = AsyncMock(return_value=None)
    repo.delete_by_arxiv_id = AsyncMock(return_value=True)
    repo.count = AsyncMock(return_value=0)
    repo.delete = AsyncMock(return_value=True)
    repo.get_orphaned_papers = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_chunk_repo():
    """Create a mock ChunkRepository."""
    repo = AsyncMock()
    repo.count = AsyncMock(return_value=0)
    repo.count_by_paper_id = AsyncMock(return_value=0)
    repo.delete_by_paper_id = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_conversation_repo():
    """Create a mock ConversationRepository."""
    repo = AsyncMock()
    repo.get_all = AsyncMock(return_value=([], 0))
    repo.get_with_turns = AsyncMock(return_value=None)
    repo.get_by_session_id = AsyncMock(return_value=None)
    repo.get_turn_count = AsyncMock(return_value=0)
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_search_service():
    """Create a mock SearchService."""
    service = AsyncMock()
    service.hybrid_search = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_ingest_service():
    """Create a mock IngestService."""
    from src.schemas.ingest import IngestResponse

    service = AsyncMock()
    service.ingest_papers = AsyncMock(
        return_value=IngestResponse(
            status="completed",
            papers_fetched=1,
            papers_processed=1,
            chunks_created=10,
            duration_seconds=1.5,
            errors=[],
        )
    )
    return service


@pytest.fixture
def mock_embeddings_client():
    """Create a mock JinaEmbeddingsClient."""
    client = AsyncMock()
    client.api_key = "test-api-key"
    client.embed_query = AsyncMock(return_value=[0.1] * 1024)
    return client


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock()
    settings.default_llm_provider = "openai"
    settings.openai_api_key = "test-openai-key"
    settings.zai_api_key = None
    settings.jina_api_key = "test-jina-key"
    settings.langfuse_enabled = False
    settings.agent_timeout_seconds = 180
    settings.debug = False
    settings.log_level = "INFO"
    settings.get_allowed_models = Mock(return_value=["gpt-4o-mini", "gpt-4o"])
    return settings


@pytest.fixture
def mock_user():
    """Create a mock User object for authentication."""
    from src.models.user import User

    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_test123"
    user.email = "test@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.profile_image_url = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.last_login_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_task_exec_repo():
    """Create a mock TaskExecutionRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_user_and_celery_task_id = AsyncMock(return_value=None)
    repo.get_by_celery_task_id = AsyncMock(return_value=None)
    repo.list_by_user = AsyncMock(return_value=([], 0))
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_report_repo():
    """Create a mock ReportRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_reports = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def mock_user_repo():
    """Create a mock UserRepository."""
    repo = AsyncMock()
    repo.update_preferences = AsyncMock()
    repo.get_or_create = AsyncMock(return_value=(Mock(), False))
    repo.get_users_with_searches = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def client(
    mock_db_session,
    mock_paper_repo,
    mock_chunk_repo,
    mock_conversation_repo,
    mock_search_service,
    mock_ingest_service,
    mock_embeddings_client,
    mock_settings,
    mock_user,
    mock_task_exec_repo,
    mock_report_repo,
    mock_user_repo,
):
    """Create TestClient with all dependencies overridden including auth."""
    from src.main import app
    from src.database import get_db
    from src.dependencies import (
        get_paper_repository,
        get_chunk_repository,
        get_conversation_repository,
        get_search_service_dep,
        get_ingest_service_dep,
        get_current_user_required,
        get_task_execution_repository,
        get_report_repository,
        get_user_repository,
    )
    from src.factories.client_factories import get_embeddings_client
    from src.config import get_settings

    # Create async generator override for get_db
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db_session

    # Override functions that return the mocks directly (no db parameter needed)
    def override_paper_repo() -> Mock:
        return mock_paper_repo

    def override_chunk_repo() -> Mock:
        return mock_chunk_repo

    def override_conversation_repo() -> Mock:
        return mock_conversation_repo

    def override_search_service() -> Mock:
        return mock_search_service

    def override_ingest_service() -> Mock:
        return mock_ingest_service

    def override_embeddings_client() -> Mock:
        return mock_embeddings_client

    def override_settings() -> Mock:
        return mock_settings

    # Override auth dependency to return mock user (no authentication required in tests)
    def override_current_user_required() -> Mock:
        return mock_user

    def override_task_exec_repo() -> Mock:
        return mock_task_exec_repo

    def override_report_repo() -> Mock:
        return mock_report_repo

    def override_user_repo() -> Mock:
        return mock_user_repo

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_paper_repository] = override_paper_repo
    app.dependency_overrides[get_chunk_repository] = override_chunk_repo
    app.dependency_overrides[get_conversation_repository] = override_conversation_repo
    app.dependency_overrides[get_search_service_dep] = override_search_service
    app.dependency_overrides[get_ingest_service_dep] = override_ingest_service
    app.dependency_overrides[get_embeddings_client] = override_embeddings_client
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_current_user_required] = override_current_user_required
    app.dependency_overrides[get_task_execution_repository] = override_task_exec_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[get_user_repository] = override_user_repo

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(
    mock_db_session,
    mock_paper_repo,
    mock_chunk_repo,
    mock_conversation_repo,
    mock_search_service,
    mock_ingest_service,
    mock_embeddings_client,
    mock_settings,
    mock_task_exec_repo,
    mock_report_repo,
    mock_user_repo,
):
    """Create TestClient WITHOUT auth override to test 401 responses."""
    from src.main import app
    from src.database import get_db
    from src.dependencies import (
        get_paper_repository,
        get_chunk_repository,
        get_conversation_repository,
        get_search_service_dep,
        get_ingest_service_dep,
        get_task_execution_repository,
        get_report_repository,
        get_user_repository,
    )
    from src.factories.client_factories import get_embeddings_client
    from src.config import get_settings

    # Create async generator override for get_db
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db_session

    # Override functions that return the mocks directly (no db parameter needed)
    def override_paper_repo() -> Mock:
        return mock_paper_repo

    def override_chunk_repo() -> Mock:
        return mock_chunk_repo

    def override_conversation_repo() -> Mock:
        return mock_conversation_repo

    def override_search_service() -> Mock:
        return mock_search_service

    def override_ingest_service() -> Mock:
        return mock_ingest_service

    def override_embeddings_client() -> Mock:
        return mock_embeddings_client

    def override_settings() -> Mock:
        return mock_settings

    def override_task_exec_repo() -> Mock:
        return mock_task_exec_repo

    def override_report_repo() -> Mock:
        return mock_report_repo

    def override_user_repo() -> Mock:
        return mock_user_repo

    # Override dependencies (NO auth override - will require real auth)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_paper_repository] = override_paper_repo
    app.dependency_overrides[get_chunk_repository] = override_chunk_repo
    app.dependency_overrides[get_conversation_repository] = override_conversation_repo
    app.dependency_overrides[get_search_service_dep] = override_search_service
    app.dependency_overrides[get_ingest_service_dep] = override_ingest_service
    app.dependency_overrides[get_embeddings_client] = override_embeddings_client
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_task_execution_repository] = override_task_exec_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[get_user_repository] = override_user_repo

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_task_registry():
    """Reset task registry between tests."""
    from src.services.task_registry import task_registry

    task_registry._tasks.clear()
    yield
    task_registry._tasks.clear()


@pytest.fixture(autouse=True)
def reset_idempotency_store():
    """Reset idempotency store between tests."""
    from src.utils.idempotency import idempotency_store

    idempotency_store._store.clear()
    yield
    idempotency_store._store.clear()


# Sample data fixtures


@pytest.fixture
def sample_task_execution():
    """Factory fixture for creating mock TaskExecution objects."""

    def _make(task_id="test-task-123", status="queued", error_message=None, completed_at=None):
        task_exec = Mock()
        task_exec.celery_task_id = task_id
        task_exec.user_id = uuid.uuid4()
        task_exec.task_type = "ingest"
        task_exec.status = status
        task_exec.error_message = error_message
        task_exec.created_at = datetime.now(timezone.utc)
        task_exec.completed_at = completed_at
        return task_exec

    return _make


@pytest.fixture
def sample_paper():
    """Create a sample paper mock object with all required fields."""
    paper = Mock()
    paper.id = uuid.uuid4()
    paper.arxiv_id = "2301.00001"
    paper.title = "Test Paper Title"
    paper.authors = ["Author One", "Author Two"]
    paper.abstract = "This is a test abstract."
    paper.categories = ["cs.LG", "cs.AI"]
    paper.published_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    paper.pdf_url = "https://arxiv.org/pdf/2301.00001.pdf"
    paper.pdf_processed = True
    paper.pdf_processing_date = datetime(2023, 1, 2, tzinfo=timezone.utc)
    paper.parser_used = "marker"
    paper.raw_text = "Raw text content of the paper."
    paper.sections = [{"name": "Introduction", "text": "Intro text."}]
    paper.created_at = datetime.now(timezone.utc)
    paper.updated_at = datetime.now(timezone.utc)
    return paper


@pytest.fixture
def sample_conversation(mock_user):
    """Create a sample conversation mock object."""
    conv = Mock()
    conv.id = uuid.uuid4()
    conv.session_id = "test-session-123"
    conv.user_id = mock_user.id
    conv.turns = []
    conv.created_at = datetime.now(timezone.utc)
    conv.updated_at = datetime.now(timezone.utc)
    return conv


@pytest.fixture
def sample_conversation_turn(sample_conversation):
    """Create a sample conversation turn mock object."""
    turn = Mock()
    turn.id = uuid.uuid4()
    turn.conversation_id = sample_conversation.id
    turn.turn_number = 0
    turn.user_query = "What is machine learning?"
    turn.agent_response = "Machine learning is a branch of AI."
    turn.provider = "openai"
    turn.model = "gpt-4o-mini"
    turn.guardrail_score = 85
    turn.retrieval_attempts = 1
    turn.rewritten_query = None
    turn.sources = []
    turn.reasoning_steps = []
    turn.created_at = datetime.now(timezone.utc)
    return turn


@pytest.fixture
def sample_search_result():
    """Create a sample SearchResult."""
    from src.repositories.search_repository import SearchResult

    return SearchResult(
        chunk_id="chunk-uuid-1",
        paper_id="paper-uuid-1",
        arxiv_id="2301.00001",
        title="Test Paper",
        authors=["Author One"],
        chunk_text="Sample chunk text for testing.",
        section_name="Introduction",
        page_number=1,
        score=0.95,
        vector_score=0.95,
        text_score=None,
        published_date="2023-01-01",
        pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
    )
