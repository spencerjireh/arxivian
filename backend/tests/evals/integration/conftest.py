"""Integration eval fixtures -- real DB, real LLM, real services."""

from __future__ import annotations

import os
from uuid import UUID

import litellm
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings
from src.factories.service_factories import get_agent_service
from src.models.user import User
from src.services.agent_service import AgentService


# ---------------------------------------------------------------------------
# Auto-apply inteval marker
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list) -> None:
    """Auto-apply inteval marker to all tests in this directory."""
    this_dir = os.path.dirname(__file__)
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
    yield engine
    # No teardown -- test-db is ephemeral via docker compose


@pytest.fixture(scope="session")
def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
async def seed_user(session_factory) -> User:
    """Get or create the integration eval test user."""
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.clerk_id == "inteval_test_user")
        )
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


@pytest.fixture
def agent_service(db_session: AsyncSession, seed_user: User) -> AgentService:
    """Production agent service wired to real DB + real LLM."""
    return get_agent_service(
        db_session,
        user_id=seed_user.id,
        temperature=0.3,
        max_iterations=5,
    )


# NOTE: adispatch_custom_event is NOT patched because ask_stream() uses
# astream_events() which requires real event dispatch for CONTENT tokens.
