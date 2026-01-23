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
    """
    Get SearchService with database session.

    Args:
        db: Database session

    Returns:
        SearchService instance
    """
    return get_search_service(db)


def get_ingest_service_dep(db: DbSession) -> IngestService:
    """
    Get IngestService with database session.

    Args:
        db: Database session

    Returns:
        IngestService instance
    """
    return get_ingest_service(db)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service_dep)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service_dep)]
ChunkingServiceDep = Annotated[ChunkingService, Depends(get_chunking_service)]
PDFParserDep = Annotated[PDFParser, Depends(get_pdf_parser)]


# Repository dependencies (request-scoped)
def get_paper_repository(db: DbSession) -> PaperRepository:
    """
    Get PaperRepository with database session.

    Args:
        db: Database session

    Returns:
        PaperRepository instance
    """
    return PaperRepository(db)


def get_chunk_repository(db: DbSession) -> ChunkRepository:
    """
    Get ChunkRepository with database session.

    Args:
        db: Database session

    Returns:
        ChunkRepository instance
    """
    return ChunkRepository(db)


def get_search_repository(db: DbSession) -> SearchRepository:
    """
    Get SearchRepository with database session.

    Args:
        db: Database session

    Returns:
        SearchRepository instance
    """
    return SearchRepository(db)


def get_conversation_repository(db: DbSession) -> ConversationRepository:
    """
    Get ConversationRepository with database session.

    Args:
        db: Database session

    Returns:
        ConversationRepository instance
    """
    return ConversationRepository(db)


PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]
SearchRepoDep = Annotated[SearchRepository, Depends(get_search_repository)]
ConversationRepoDep = Annotated[ConversationRepository, Depends(get_conversation_repository)]


# ============================================================================
# User Repository
# ============================================================================


def get_user_repository(db: DbSession) -> UserRepository:
    """
    Get UserRepository with database session.

    Args:
        db: Database session

    Returns:
        UserRepository instance
    """
    return UserRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user_optional(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Use this dependency when authentication is optional (e.g., guest access).
    The user will be synced/created in the database on first authenticated request.

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        User if authenticated, None if no valid token
    """
    if not authorization:
        return None

    try:
        auth_service = get_auth_service()
        auth_user = await auth_service.verify_token(authorization)

        # Sync user to database
        user_repo = UserRepository(db)
        user, created = await user_repo.get_or_create(
            clerk_id=auth_user.clerk_id,
            email=auth_user.email,
            first_name=auth_user.first_name,
            last_name=auth_user.last_name,
            profile_image_url=auth_user.profile_image_url,
        )
        await db.commit()

        return user
    except Exception:
        # For optional auth, swallow errors and return None
        return None


async def get_current_user_required(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user, raise 401 if not authenticated.

    Use this dependency when authentication is required.
    The user will be synced/created in the database on first authenticated request.

    Args:
        authorization: Authorization header value
        db: Database session

    Returns:
        Authenticated User

    Raises:
        MissingTokenError: If no token provided
        InvalidTokenError: If token is invalid
    """
    if not authorization:
        raise MissingTokenError()

    auth_service = get_auth_service()
    auth_user = await auth_service.verify_token(authorization)

    # Sync user to database
    user_repo = UserRepository(db)
    user, created = await user_repo.get_or_create(
        clerk_id=auth_user.clerk_id,
        email=auth_user.email,
        first_name=auth_user.first_name,
        last_name=auth_user.last_name,
        profile_image_url=auth_user.profile_image_url,
    )
    await db.commit()

    return user


# Type aliases for auth dependencies
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
CurrentUserRequired = Annotated[User, Depends(get_current_user_required)]
