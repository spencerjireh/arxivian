"""FastAPI dependency injection providers."""

import hmac
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.services.search_service import SearchService
from src.services.ingest_service import IngestService
from src.services.auth_service import get_auth_service
from src.utils.chunking_service import ChunkingService
from src.utils.pdf_parser import PDFParser
from src.repositories.paper_repository import PaperRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.search_repository import SearchRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.user_repository import UserRepository
from src.repositories.task_execution_repository import TaskExecutionRepository
from src.repositories.usage_counter_repository import UsageCounterRepository
from src.models.user import User
from src.config import Settings, get_settings
from src.tiers import TierPolicy, get_policy
from src.exceptions import InvalidApiKeyError, MissingTokenError, UsageLimitExceededError

from src.utils.logger import get_logger
from src.factories.client_factories import (
    get_arxiv_client,
    get_embeddings_client,
)
from src.factories.service_factories import (
    get_search_service,
    get_chunking_service,
    get_pdf_parser,
    get_ingest_service,
)

log = get_logger(__name__)


# Type aliases for cleaner router signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Client dependencies (singletons)
ArxivClientDep = Annotated[ArxivClient, Depends(get_arxiv_client)]
EmbeddingsClientDep = Annotated[JinaEmbeddingsClient, Depends(get_embeddings_client)]


# Service dependencies
def get_search_service_dep(db: DbSession) -> SearchService:
    """Get SearchService with database session."""
    return get_search_service(db)


def get_ingest_service_dep(db: DbSession) -> IngestService:
    """Get IngestService with database session."""
    return get_ingest_service(db)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service_dep)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service_dep)]
ChunkingServiceDep = Annotated[ChunkingService, Depends(get_chunking_service)]
PDFParserDep = Annotated[PDFParser, Depends(get_pdf_parser)]


# Repository dependencies (request-scoped)
def get_paper_repository(db: DbSession) -> PaperRepository:
    """Get PaperRepository with database session."""
    return PaperRepository(db)


def get_chunk_repository(db: DbSession) -> ChunkRepository:
    """Get ChunkRepository with database session."""
    return ChunkRepository(db)


def get_search_repository(db: DbSession) -> SearchRepository:
    """Get SearchRepository with database session."""
    return SearchRepository(db)


def get_conversation_repository(db: DbSession) -> ConversationRepository:
    """Get ConversationRepository with database session."""
    return ConversationRepository(db)


PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]
SearchRepoDep = Annotated[SearchRepository, Depends(get_search_repository)]
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
    await db.commit()
    return user


async def get_current_user_optional(
    db: DbSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    if not authorization:
        return None

    try:
        return await _sync_user(authorization, db)
    except Exception:
        return None


async def get_current_user_required(
    db: DbSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    """Get current user, raise 401 if not authenticated."""
    if not authorization:
        raise MissingTokenError()

    return await _sync_user(authorization, db)


# Type aliases for auth dependencies
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentUserRequired = Annotated[User, Depends(get_current_user_required)]


# ============================================================================
# Redis Dependency
# ============================================================================


async def get_redis(request: Request) -> Redis:
    """Get async Redis client from app state."""
    return request.app.state.redis


RedisDep = Annotated[Redis, Depends(get_redis)]


# ============================================================================
# Tier Policy + Rate Limit Dependencies
# ============================================================================


async def get_tier_policy(user: CurrentUserOptional) -> TierPolicy:
    """Resolve tier policy from user. No rate-limit enforcement."""
    return get_policy(user)


TierPolicyDep = Annotated[TierPolicy, Depends(get_tier_policy)]


async def enforce_chat_limit(
    user: CurrentUserOptional,
    policy: TierPolicyDep,
    request: Request,
    redis: RedisDep,
    db: DbSession,
) -> None:
    """Enforce daily chat limit. Raises 429 if exceeded."""
    if policy.daily_chats is None:
        return  # Pro -- unlimited

    if user is None:
        # Anonymous: Redis-based, atomic INCR keyed by IP + UTC date
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        today_utc = datetime.now(timezone.utc).date()
        key = f"anon_chats:{ip}:{today_utc}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 86400)
    else:
        # Authenticated: DB-based
        usage_repo = UsageCounterRepository(db)
        count = await usage_repo.get_today_query_count(str(user.id))

    if count > policy.daily_chats:
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
