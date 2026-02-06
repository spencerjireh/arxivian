"""Integration test configuration with real PostgreSQL database."""

import os
import uuid
import random
import pytest
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from alembic.config import Config
from alembic import command

from src.database import Base


# Test database URL from environment or default
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/arxiv_rag_test",
)


def pytest_collection_modifyitems(items):
    """Apply integration marker to all tests in this directory."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Return the event loop policy for session scope."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine (session-scoped)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def setup_database(test_engine: AsyncEngine):
    """
    Setup test database with pgvector extension and run migrations.

    Runs once at the start of the test session.
    """
    async with test_engine.begin() as conn:
        # Ensure pgvector extension is installed
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Drop all tables including alembic_version for a completely clean slate
        # This ensures migrations run from scratch every time
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Run Alembic migrations synchronously
    def run_migrations():
        alembic_cfg = Config("alembic.ini")
        # Convert async URL to sync for alembic
        sync_url = TEST_DATABASE_URL.replace("+asyncpg", "")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(alembic_cfg, "head")

    await asyncio.get_event_loop().run_in_executor(None, run_migrations)

    yield

    # Cleanup after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def async_session_factory(
    test_engine: AsyncEngine, setup_database
) -> async_sessionmaker[AsyncSession]:
    """Create session factory (session-scoped)."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
async def db_session(
    test_engine: AsyncEngine,
    setup_database,  # Ensure migrations run before tests
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session with transaction rollback for test isolation.

    Uses a nested transaction (savepoint) approach so that commits within
    tests don't close the outer transaction. The outer transaction is
    rolled back at the end, providing test isolation.
    """
    from sqlalchemy import event

    # Create a connection and start an outer transaction
    async with test_engine.connect() as conn:
        trans = await conn.begin()

        # Create a session bound to this connection
        async_session = AsyncSession(bind=conn, expire_on_commit=False)

        # Begin a nested transaction (savepoint)
        nested = await conn.begin_nested()

        # Listen for session commit events and restart the nested savepoint
        @event.listens_for(async_session.sync_session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                # The nested savepoint was committed, start a new one
                session.begin_nested()

        yield async_session

        await async_session.close()
        # Rollback the outer transaction - this discards all changes
        await trans.rollback()


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_paper_data() -> dict:
    """Sample paper data for testing."""
    return {
        "arxiv_id": f"2301.{uuid.uuid4().hex[:5]}",
        "title": "Test Paper: Machine Learning Approaches",
        "authors": ["Alice Smith", "Bob Jones"],
        "abstract": "This paper explores novel machine learning techniques.",
        "categories": ["cs.LG", "cs.AI"],
        "published_date": datetime(2023, 1, 15, tzinfo=timezone.utc),
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
    }


@pytest.fixture
def sample_processed_paper_data(sample_paper_data) -> dict:
    """Sample paper data with processed content."""
    return {
        **sample_paper_data,
        "pdf_processed": True,
        "pdf_processing_date": datetime.now(timezone.utc),
        "parser_used": "marker",
        "raw_text": "Full text content of the paper...",
        "sections": [
            {"name": "Introduction", "text": "This paper introduces..."},
            {"name": "Methods", "text": "We use the following methods..."},
        ],
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample 1024-dimensional embedding vector."""
    random.seed(42)
    return [random.uniform(-1, 1) for _ in range(1024)]


def make_chunk_data(
    paper_id: uuid.UUID,
    arxiv_id: str,
    chunk_index: int,
    embedding: list[float],
    section_name: str = "Introduction",
    chunk_text: str | None = None,
) -> dict:
    """Factory for creating chunk data."""
    return {
        "paper_id": paper_id,
        "arxiv_id": arxiv_id,
        "chunk_text": chunk_text or f"This is chunk {chunk_index} content about machine learning.",
        "chunk_index": chunk_index,
        "section_name": section_name,
        "page_number": chunk_index + 1,
        "word_count": 10,
        "embedding": embedding,
    }


# =============================================================================
# User Data Fixtures
# =============================================================================


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data dict for creation."""
    return {
        "clerk_id": f"user_{uuid.uuid4().hex[:16]}",
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "profile_image_url": "https://example.com/avatar.png",
    }


@pytest.fixture
async def created_user(db_session, sample_user_data):
    """Create and return a user in the test database."""
    from src.repositories.user_repository import UserRepository

    repo = UserRepository(session=db_session)
    user = await repo.create(
        clerk_id=sample_user_data["clerk_id"],
        email=sample_user_data["email"],
        first_name=sample_user_data["first_name"],
        last_name=sample_user_data["last_name"],
        profile_image_url=sample_user_data["profile_image_url"],
    )
    return user
