"""Integration eval fixtures -- real DB, real LLM, real services."""

from __future__ import annotations

from pathlib import Path

import litellm
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings
from src.factories import get_agent_service
from src.models.user import User
from src.repositories.paper_repository import PaperRepository
from src.services.agent_service import AgentService
from src.services.agent_service.context import ScopedPaper
from src.services.agent_service.graph_builder import build_graph

# ---------------------------------------------------------------------------
# Auto-apply inteval marker
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list) -> None:
    """Auto-apply inteval marker to all tests in this directory."""
    this_dir = str(Path(__file__).parent)
    for item in items:
        if str(item.fspath).startswith(this_dir):
            item.add_marker(pytest.mark.inteval)


# ---------------------------------------------------------------------------
# Session-scoped: LiteLLM config, DB engine, session factory, seed user
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _configure_litellm() -> None:
    """Drop unsupported params for reasoning models."""
    litellm.drop_params = True


@pytest.fixture(scope="session")
def db_engine():
    settings = get_settings()
    engine = create_async_engine(
        settings.postgres_url,
        echo=False,
        pool_pre_ping=True,
    )
    return engine
    # No teardown -- test-db is ephemeral via docker compose


@pytest.fixture(scope="session")
def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
async def seed_user(session_factory) -> User:
    """Get or create the integration eval test user."""
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.clerk_id == "inteval_test_user"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(clerk_id="inteval_test_user", email="inteval@test.local")
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# Function-scoped: fresh DB session + agent service per test
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session(session_factory):
    """Fresh AsyncSession per test, with rollback on failure."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(scope="session")
def compiled_graph():
    return build_graph()


@pytest.fixture
def agent_for(db_session: AsyncSession, seed_user: User, compiled_graph):
    """Factory: the production agent service scoped to one seeded paper.

    Every conversation is paper-scoped (Phase 3); a test picks the paper its query is
    about. Skips when the paper did not seed (see `scenarios.UNINGESTABLE`).
    """

    async def _build(arxiv_id: str) -> AgentService:
        paper = await PaperRepository(db_session).get_by_arxiv_id(arxiv_id)
        if paper is None or not paper.pdf_processed:
            pytest.skip(f"Seed paper {arxiv_id} is not ingested; run `just inteval-seed`")
        scope = ScopedPaper(paper_id=str(paper.id), arxiv_id=paper.arxiv_id, title=paper.title)
        return get_agent_service(
            db_session, user_id=seed_user.id, graph=compiled_graph, scoped_paper=scope
        )

    return _build


# NOTE: adispatch_custom_event is NOT patched because ask_stream() uses
# astream_events() which requires real event dispatch for CONTENT tokens.
