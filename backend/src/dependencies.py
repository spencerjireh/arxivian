"""FastAPI dependency injection providers."""

import hmac
from typing import Annotated

from fastapi import Depends, Header, Request
from langgraph.graph.state import CompiledStateGraph
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.embeddings_client import JinaEmbeddingsClient
from src.config import Settings, get_settings
from src.database import get_db
from src.exceptions import (
    InvalidApiKeyError,
    MissingTokenError,
    UsageLimitExceededError,
)
from src.factories import (
    get_auth_service,
    get_embeddings_client,
    get_feed_service,
    get_search_service,
)
from src.models.user import User
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.task_execution_repository import TaskExecutionRepository
from src.repositories.usage_counter_repository import UsageCounterRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.repositories.user_repository import UserRepository
from src.services.feed_service import FeedService
from src.services.search_service import SearchService
from src.tiers import TierPolicy, get_policy
from src.utils.logger import get_logger

log = get_logger(__name__)


# Type aliases for cleaner router signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Client dependencies (singletons)
EmbeddingsClientDep = Annotated[JinaEmbeddingsClient, Depends(get_embeddings_client)]


# Service dependencies
def get_search_service_dep(db: DbSession) -> SearchService:
    """Get SearchService with database session."""
    return get_search_service(db)


def get_feed_service_dep(db: DbSession) -> FeedService:
    """Get FeedService with database session."""
    return get_feed_service(db)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service_dep)]
FeedServiceDep = Annotated[FeedService, Depends(get_feed_service_dep)]


# Repository dependencies (request-scoped)
def get_paper_repository(db: DbSession) -> PaperRepository:
    """Get PaperRepository with database session."""
    return PaperRepository(db)


def get_chunk_repository(db: DbSession) -> ChunkRepository:
    """Get ChunkRepository with database session."""
    return ChunkRepository(db)


def get_conversation_repository(db: DbSession) -> ConversationRepository:
    """Get ConversationRepository with database session."""
    return ConversationRepository(db)


PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]
ConversationRepoDep = Annotated[ConversationRepository, Depends(get_conversation_repository)]


# ============================================================================
# User Repository
# ============================================================================


def get_user_repository(db: DbSession) -> UserRepository:
    """Get UserRepository with database session."""
    return UserRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


# ============================================================================
# Task Execution Repository
# ============================================================================


def get_task_execution_repository(db: DbSession) -> TaskExecutionRepository:
    """Get TaskExecutionRepository with database session."""
    return TaskExecutionRepository(db)


TaskExecRepoDep = Annotated[TaskExecutionRepository, Depends(get_task_execution_repository)]


# ============================================================================
# Usage Counter Repository
# ============================================================================


def get_usage_counter_repository(db: DbSession) -> UsageCounterRepository:
    """Get UsageCounterRepository with database session."""
    return UsageCounterRepository(db)


UsageCounterRepoDep = Annotated[UsageCounterRepository, Depends(get_usage_counter_repository)]


# ============================================================================
# Feed-pivot repositories (per-user paper state)
# ============================================================================


def get_user_paper_state_repository(db: DbSession) -> UserPaperStateRepository:
    """Get UserPaperStateRepository with database session."""
    return UserPaperStateRepository(db)


UserPaperStateRepoDep = Annotated[
    UserPaperStateRepository, Depends(get_user_paper_state_repository)
]


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def _sync_user(authorization: str, db: AsyncSession) -> User:
    """Verify token and sync user to database."""
    auth_service = get_auth_service()
    auth_user = await auth_service.verify_token(authorization)
    user_repo = UserRepository(db)
    user, _ = await user_repo.get_or_create(
        clerk_id=auth_user.clerk_id,
        email=auth_user.email,
        first_name=auth_user.first_name,
        last_name=auth_user.last_name,
        profile_image_url=auth_user.profile_image_url,
    )
    return user


async def get_current_user_required(
    db: DbSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    """Get current user, raise 401 if not authenticated."""
    if not authorization:
        raise MissingTokenError()

    return await _sync_user(authorization, db)


# Type aliases for auth dependencies
CurrentUserRequired = Annotated[User, Depends(get_current_user_required)]


# ============================================================================
# Redis Dependency
# ============================================================================


def get_redis(request: Request) -> Redis:
    """Get async Redis client from app state."""
    return request.app.state.redis


RedisDep = Annotated[Redis, Depends(get_redis)]


# ============================================================================
# Agent Graph Dependency
# ============================================================================


def get_agent_graph(request: Request) -> CompiledStateGraph:
    """Get compiled LangGraph agent graph from app state."""
    return request.app.state.agent_graph


AgentGraphDep = Annotated[CompiledStateGraph, Depends(get_agent_graph)]


# ============================================================================
# Tier Policy + Rate Limit Dependencies
# ============================================================================


async def get_tier_policy(user: CurrentUserRequired) -> TierPolicy:
    """Resolve tier policy from authenticated user."""
    return get_policy(user)


TierPolicyDep = Annotated[TierPolicy, Depends(get_tier_policy)]


async def enforce_chat_limit(
    user: CurrentUserRequired,
    policy: TierPolicyDep,
    usage_repo: UsageCounterRepoDep,
) -> None:
    """Enforce daily chat limit. Raises 429 if exceeded."""
    if policy.daily_chats is None:
        return  # Pro -- unlimited

    count = await usage_repo.get_today_query_count(str(user.id))

    if count >= policy.daily_chats:
        raise UsageLimitExceededError(current=count, limit=policy.daily_chats)


ChatGuard = Annotated[None, Depends(enforce_chat_limit)]


# ============================================================================
# API Key Dependencies
# ============================================================================


def verify_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Verify the X-Api-Key header matches the configured API key."""
    if not settings.api_key or not x_api_key:
        log.warning("ops api key rejected", reason="missing key or unconfigured")
        raise InvalidApiKeyError()
    if not hmac.compare_digest(x_api_key, settings.api_key):
        log.warning("ops api key rejected", reason="key mismatch")
        raise InvalidApiKeyError()


ApiKeyCheck = Annotated[None, Depends(verify_api_key)]
