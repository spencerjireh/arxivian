"""Factory functions for business logic services."""

from functools import lru_cache
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import get_settings
from src.services.search_service import SearchService
from src.services.agent_service import AgentService
from src.services.ingest_service import IngestService
from src.utils.chunking_service import ChunkingService
from src.utils.pdf_parser import PDFParser
from src.factories.client_factories import (
    get_embeddings_client,
    get_llm_client,
    get_arxiv_client,
)
from src.repositories.paper_repository import PaperRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.search_repository import SearchRepository
from src.repositories.conversation_repository import ConversationRepository


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
        min_chunk_words=settings.min_chunk_words,
    )


@lru_cache(maxsize=1)
def get_pdf_parser() -> PDFParser:
    """
    Create singleton PDF parser.

    Returns:
        PDFParser instance
    """
    return PDFParser()


def get_ingest_service(
    db_session: AsyncSession, ingested_by: str | None = None
) -> IngestService:
    """
    Create IngestService with dependencies.

    Note: Not cached because depends on request-scoped db session.

    Args:
        db_session: Database session
        ingested_by: Audit trail -- user who triggered the ingestion

    Returns:
        IngestService instance
    """
    arxiv_client = get_arxiv_client()
    pdf_parser = get_pdf_parser()
    embeddings_client = get_embeddings_client()
    chunking_service = get_chunking_service()
    paper_repository = PaperRepository(db_session)
    chunk_repository = ChunkRepository(db_session)

    return IngestService(
        arxiv_client=arxiv_client,
        pdf_parser=pdf_parser,
        embeddings_client=embeddings_client,
        chunking_service=chunking_service,
        paper_repository=paper_repository,
        chunk_repository=chunk_repository,
        ingested_by=ingested_by,
    )


def get_agent_service(
    db_session: AsyncSession,
    user_id: UUID,
    provider: str | None = None,
    model: str | None = None,
    guardrail_threshold: int = 75,
    top_k: int = 3,
    max_retrieval_attempts: int = 3,
    temperature: float = 0.3,
    session_id: str | None = None,
    conversation_window: int = 5,
    max_iterations: int = 5,
    can_ingest: bool = True,
    can_search_arxiv: bool = True,
) -> AgentService:
    """
    Create agent service with specified LLM model.

    Args:
        db_session: Database session
        user_id: User ID for conversation ownership
        provider: LLM provider prefix (e.g. 'openai', 'nvidia_nim'). Combined with
                  model into LiteLLM format. Uses system default if both None.
        model: Model name or full LiteLLM model string. Uses default if None.
        guardrail_threshold: Minimum guardrail score
        top_k: Number of chunks to use
        max_retrieval_attempts: Max query rewrites
        temperature: Generation temperature
        session_id: Optional session ID for conversation continuity
        conversation_window: Number of previous turns to include in context
        max_iterations: Maximum router iterations for tool execution
        can_ingest: Whether the ingest tool is available (tier-gated)
        can_search_arxiv: Whether the arxiv_search tool is available (tier-gated)

    Returns:
        AgentService instance
    """
    # Build LiteLLM model string from provider + model if both provided
    litellm_model: str | None = None
    if provider and model:
        litellm_model = f"{provider}/{model}"
    elif model:
        litellm_model = model

    # Get LLM client (validates model)
    llm_client = get_llm_client(model=litellm_model)

    # Get search service
    search_service = get_search_service(db_session)

    # Conditionally create services based on tier policy
    user_id_str = str(user_id)
    ingest_service = get_ingest_service(db_session, ingested_by=user_id_str) if can_ingest else None
    arxiv_client = get_arxiv_client() if can_search_arxiv else None

    # Paper repository: get from ingest_service if available, otherwise create directly
    if ingest_service is not None:
        paper_repository = ingest_service.paper_repository
    else:
        paper_repository = PaperRepository(db_session)

    # Get conversation repository for persistence
    conversation_repo = ConversationRepository(db_session)

    return AgentService(
        llm_client=llm_client,
        search_service=search_service,
        ingest_service=ingest_service,
        arxiv_client=arxiv_client,
        paper_repository=paper_repository,
        conversation_repo=conversation_repo,
        conversation_window=conversation_window,
        guardrail_threshold=guardrail_threshold,
        top_k=top_k,
        max_retrieval_attempts=max_retrieval_attempts,
        max_iterations=max_iterations,
        temperature=temperature,
        user_id=user_id,
    )
