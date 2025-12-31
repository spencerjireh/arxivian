"""Shared pytest fixtures for repository tests."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, MagicMock
from contextlib import asynccontextmanager
from datetime import datetime, timezone


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
def mock_result():
    """Create a configurable mock result object."""

    def _create_result(
        scalar_one_or_none_value=None,
        scalar_one_value=0,
        scalars_all_value=None,
        fetchall_value=None,
        rowcount=0,
    ):
        result = Mock()
        result.scalar_one_or_none = Mock(return_value=scalar_one_or_none_value)
        result.scalar_one = Mock(return_value=scalar_one_value)
        result.scalars = Mock(
            return_value=Mock(all=Mock(return_value=scalars_all_value or []))
        )
        result.fetchall = Mock(return_value=fetchall_value or [])
        result.rowcount = rowcount
        return result

    return _create_result


@pytest.fixture
def sample_paper_id():
    """Return a sample paper UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_paper_data():
    """Return sample paper data dict."""
    return {
        "arxiv_id": "2301.00001",
        "title": "Test Paper Title",
        "authors": ["Author One", "Author Two"],
        "abstract": "This is a test abstract for unit testing.",
        "categories": ["cs.LG", "cs.AI"],
        "published_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
    }


@pytest.fixture
def sample_chunk_data(sample_paper_id):
    """Return sample chunk data dict."""
    return {
        "paper_id": sample_paper_id,
        "arxiv_id": "2301.00001",
        "chunk_text": "Sample chunk text content for testing.",
        "chunk_index": 0,
        "section_name": "Introduction",
        "page_number": 1,
        "word_count": 7,
        "embedding": [0.1] * 1024,
    }


@pytest.fixture
def mock_paper(sample_paper_id):
    """Create a mock Paper model."""
    paper = Mock()
    paper.id = uuid.UUID(sample_paper_id)
    paper.arxiv_id = "2301.00001"
    paper.title = "Test Paper"
    paper.authors = ["Author One"]
    paper.abstract = "Test abstract content."
    paper.categories = ["cs.LG"]
    paper.published_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    paper.pdf_url = "https://arxiv.org/pdf/2301.00001.pdf"
    paper.pdf_processed = True
    paper.raw_text = "Raw text content."
    paper.sections = [{"name": "Introduction", "text": "Intro text."}]
    paper.created_at = datetime.now(timezone.utc)
    paper.updated_at = datetime.now(timezone.utc)
    return paper


@pytest.fixture
def mock_chunk(sample_paper_id):
    """Create a mock Chunk model."""
    chunk = Mock()
    chunk.id = uuid.uuid4()
    chunk.paper_id = uuid.UUID(sample_paper_id)
    chunk.arxiv_id = "2301.00001"
    chunk.chunk_text = "Sample chunk text."
    chunk.chunk_index = 0
    chunk.section_name = "Introduction"
    chunk.page_number = 1
    chunk.word_count = 4
    chunk.embedding = [0.1] * 1024
    return chunk


@pytest.fixture
def mock_conversation():
    """Create a mock Conversation model."""
    conv = Mock()
    conv.id = uuid.uuid4()
    conv.session_id = "test-session-123"
    conv.turns = []
    conv.created_at = datetime.now(timezone.utc)
    conv.updated_at = datetime.now(timezone.utc)
    return conv


@pytest.fixture
def mock_conversation_turn(mock_conversation):
    """Create a mock ConversationTurn model."""
    turn = Mock()
    turn.id = uuid.uuid4()
    turn.conversation_id = mock_conversation.id
    turn.turn_number = 0
    turn.user_query = "What is machine learning?"
    turn.agent_response = "Machine learning is a branch of AI."
    turn.guardrail_score = 85
    turn.retrieval_attempts = 1
    turn.rewritten_query = None
    turn.sources = []
    turn.reasoning_steps = []
    turn.provider = "openai"
    turn.model = "gpt-4"
    return turn


@pytest.fixture
def mock_agent_execution():
    """Create a mock AgentExecution model."""
    execution = Mock()
    execution.id = uuid.uuid4()
    execution.session_id = "test-session-123"
    execution.state_snapshot = {"messages": [], "iteration": 0}
    execution.status = "running"
    execution.iteration = 0
    execution.pause_reason = None
    execution.error_message = None
    execution.created_at = datetime.now(timezone.utc)
    execution.updated_at = datetime.now(timezone.utc)
    return execution


@pytest.fixture
def sample_turn_data():
    """Create sample TurnData for testing."""
    from src.schemas.conversation import TurnData

    return TurnData(
        user_query="What is deep learning?",
        agent_response="Deep learning is a subset of machine learning.",
        guardrail_score=90,
        retrieval_attempts=1,
        rewritten_query=None,
        sources=[],
        reasoning_steps=[],
        provider="openai",
        model="gpt-4",
    )


def create_mock_db_row(**kwargs):
    """Create a mock database row object with named attributes."""
    row = Mock()
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row
