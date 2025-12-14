"""Factory functions for business logic services."""

from functools import lru_cache
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import get_settings
from src.services.search_service import SearchService
from src.services.chunking_service import ChunkingService
from src.services.pdf_parser import PDFParser
from src.services.agentic_rag_service import AgenticRAGService
from src.services.factories.client_factories import get_embeddings_client, get_openai_client
from src.repositories.search_repository import SearchRepository


def get_search_service(db_session: AsyncSession) -> SearchService:
    """
    Create SearchService with dependencies.

    Note: Not cached because depends on request-scoped db session.

    Args:
        db_session: Database session

    Returns:
        SearchService instance
    """
    settings = get_settings()
    search_repo = SearchRepository(db_session)
    embeddings_client = get_embeddings_client()

    return SearchService(
        search_repository=search_repo, embeddings_client=embeddings_client, rrf_k=settings.rrf_k
    )


@lru_cache(maxsize=1)
def get_chunking_service() -> ChunkingService:
    """
    Create singleton chunking service.

    Returns:
        ChunkingService instance
    """
    settings = get_settings()
    return ChunkingService(
        target_words=settings.chunk_size_words,
        overlap_words=settings.chunk_overlap_words,
        min_words=settings.min_chunk_words,
    )


@lru_cache(maxsize=1)
def get_pdf_parser() -> PDFParser:
    """
    Create singleton PDF parser.

    Returns:
        PDFParser instance
    """
    return PDFParser()


def get_agentic_rag_service(
    db_session: AsyncSession,
    model_name: Optional[str] = None,
    guardrail_threshold: Optional[int] = None,
    top_k: Optional[int] = None,
    max_retrieval_attempts: Optional[int] = None,
) -> AgenticRAGService:
    """
    Create AgenticRAGService with dependencies.

    Note: Not cached because depends on request-scoped db session.
    Args from request override settings defaults.

    Args:
        db_session: Database session
        model_name: Optional model override
        guardrail_threshold: Optional threshold override
        top_k: Optional top_k override
        max_retrieval_attempts: Optional max attempts override

    Returns:
        AgenticRAGService instance
    """
    settings = get_settings()

    search_service = get_search_service(db_session)
    openai_client = get_openai_client()

    return AgenticRAGService(
        openai_client=openai_client,
        search_service=search_service,
        model_name=model_name or settings.openai_model,
        guardrail_threshold=guardrail_threshold or settings.guardrail_threshold,
        top_k=top_k or settings.default_top_k,
        max_retrieval_attempts=max_retrieval_attempts or settings.max_retrieval_attempts,
        temperature=0.3,
    )
