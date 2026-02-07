"""FastAPI dependency injection providers."""

from typing import Annotated, Optional
from fastapi import Depends, Header
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
from src.repositories.report_repository import ReportRepository
from src.models.user import User
from src.exceptions import MissingTokenError

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
# Report Repository
# ============================================================================


def get_report_repository(db: DbSession) -> ReportRepository:
    """Get ReportRepository with database session."""
    return ReportRepository(db)


ReportRepoDep = Annotated[ReportRepository, Depends(get_report_repository)]


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
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not authorization:
        return None

    try:
        return await _sync_user(authorization, db)
    except Exception:
        return None


async def get_current_user_required(
    db: DbSession,
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> User:
    """Get current user, raise 401 if not authenticated."""
    if not authorization:
        raise MissingTokenError()

    return await _sync_user(authorization, db)


# Type aliases for auth dependencies
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
CurrentUserRequired = Annotated[User, Depends(get_current_user_required)]
