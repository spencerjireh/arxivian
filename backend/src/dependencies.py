"""FastAPI dependency injection providers."""

from typing import Annotated, AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.clients.openai_client import OpenAIClient
from src.services.search_service import SearchService
from src.services.ingest_service import IngestService
from src.utils.chunking_service import ChunkingService
from src.utils.pdf_parser import PDFParser
from src.repositories.paper_repository import PaperRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.search_repository import SearchRepository

from src.factories.client_factories import (
    get_arxiv_client,
    get_embeddings_client,
    get_openai_client,
)
from src.factories.service_factories import (
    get_search_service,
    get_chunking_service,
    get_pdf_parser,
    get_ingest_service,
)


# Database dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for request.

    Yields:
        AsyncSession instance
    """
    async for session in get_db():
        yield session


# Type aliases for cleaner router signatures
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# Client dependencies (singletons)
ArxivClientDep = Annotated[ArxivClient, Depends(get_arxiv_client)]
EmbeddingsClientDep = Annotated[JinaEmbeddingsClient, Depends(get_embeddings_client)]
OpenAIClientDep = Annotated[OpenAIClient, Depends(get_openai_client)]


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


PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]
SearchRepoDep = Annotated[SearchRepository, Depends(get_search_repository)]
