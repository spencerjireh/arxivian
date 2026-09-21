"""Construction of clients, services and agent contexts.

One module so that FastAPI dependencies (`src/dependencies.py`) and Celery tasks build
objects the same way. Singletons are `lru_cache`d; anything that needs a db session is
built per request/task.
"""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.arxiv_client import ArxivClient
from src.clients.base_llm_client import BaseLLMClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.clients.litellm_client import LiteLLMClient
from src.clients.semantic_scholar_client import SemanticScholarClient
from src.clients.typesafe_client import TypeSafeClient
from src.config import get_settings
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.repositories.search_repository import SearchRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.services.agent_service import AgentService
from src.services.agent_service.context import ScopedPaper
from src.services.auth_service import AuthService
from src.services.chunking_service import ChunkingService
from src.services.feed_service import FeedService
from src.services.feed_service.digest import category_key_for
from src.services.ingest_service import IngestService
from src.services.scoring_service.context import ScoringContext
from src.services.scoring_service.state import RUBRIC_VERSION
from src.services.search_service import SearchService
from src.utils.pdf_parser import PDFParser

# ---------------------------------------------------------------------------
# Client singletons
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_arxiv_client() -> ArxivClient:
    return ArxivClient()


@lru_cache(maxsize=1)
def get_embeddings_client() -> JinaEmbeddingsClient:
    settings = get_settings()
    return JinaEmbeddingsClient(api_key=settings.jina_api_key, model="jina-embeddings-v3")


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        allowed_domain=settings.clerk_domain,
        audience=settings.clerk_jwt_audience or None,
    )


@lru_cache(maxsize=1)
def get_semantic_scholar_client() -> SemanticScholarClient:
    settings = get_settings()
    return SemanticScholarClient(
        api_key=settings.semantic_scholar_api_key,
        cache_ttl_seconds=settings.semantic_scholar_cache_ttl_seconds,
        min_interval_ms=settings.semantic_scholar_min_interval_ms,
    )


@lru_cache(maxsize=1)
def _default_typesafe_client() -> TypeSafeClient:
    settings = get_settings()
    return TypeSafeClient(
        api_key=settings.typesafe_api_key,
        model=settings.typesafe_model,
        timeout_seconds=settings.typesafe_timeout_seconds,
    )


def get_typesafe_client(model: str | None = None) -> TypeSafeClient:
    """The TypeSafe Jev client for Stage 2 scoring judgments.

    Cached for the configured default model; a `model` override (evals) builds a fresh
    instance. Raises `TypeSafeError` when `TYPESAFE_API_KEY` is unset, so never call this
    at import time -- only from the scoring task / eval fixtures.
    """
    if model is None:
        return _default_typesafe_client()
    settings = get_settings()
    return TypeSafeClient(
        api_key=settings.typesafe_api_key,
        model=model,
        timeout_seconds=settings.typesafe_timeout_seconds,
    )


def get_llm_client() -> BaseLLMClient:
    """The LiteLLM client for `DEFAULT_LLM_MODEL` (structured calls may use
    `STRUCTURED_OUTPUT_MODEL`). There is no per-request model selection."""
    settings = get_settings()
    return LiteLLMClient(
        model=settings.default_llm_model,
        timeout=float(settings.llm_call_timeout_seconds),
        structured_output_model=settings.structured_output_model or None,
    )


# ---------------------------------------------------------------------------
# Services (per session unless noted)
# ---------------------------------------------------------------------------


def get_search_service(db_session: AsyncSession) -> SearchService:
    settings = get_settings()
    return SearchService(
        search_repository=SearchRepository(db_session),
        embeddings_client=get_embeddings_client(),
        rrf_k=settings.rrf_k,
    )


@lru_cache(maxsize=1)
def get_chunking_service() -> ChunkingService:
    settings = get_settings()
    return ChunkingService(
        target_words=settings.chunk_size_words,
        overlap_words=settings.chunk_overlap_words,
        min_chunk_words=settings.min_chunk_words,
    )


@lru_cache(maxsize=1)
def get_pdf_parser() -> PDFParser:
    return PDFParser()


def get_ingest_service(db_session: AsyncSession, ingested_by: str | None = None) -> IngestService:
    """`ingested_by` is the audit trail: the user or task that triggered the ingestion."""
    return IngestService(
        arxiv_client=get_arxiv_client(),
        pdf_parser=get_pdf_parser(),
        embeddings_client=get_embeddings_client(),
        chunking_service=get_chunking_service(),
        paper_repository=PaperRepository(db_session),
        chunk_repository=ChunkRepository(db_session),
        ingested_by=ingested_by,
    )


def get_scoring_context(db_session: AsyncSession) -> ScoringContext:
    """A ScoringContext for one Stage 2 scoring run (all judgments via TypeSafe Jev)."""
    return ScoringContext(
        typesafe_client=get_typesafe_client(),
        semantic_scholar_client=get_semantic_scholar_client(),
        ingest_service=get_ingest_service(db_session),
        search_service=get_search_service(db_session),
        paper_repository=PaperRepository(db_session),
        scoring_repository=ScoringRepository(db_session),
        db_session=db_session,
        rubric_version=RUBRIC_VERSION,
    )


def get_feed_service(db_session: AsyncSession) -> FeedService:
    """FeedService over the request session. The digest key is the triage category set,
    matching what `build_digest_task` writes."""
    settings = get_settings()
    return FeedService(
        digest_repo=DigestRepository(db_session),
        scoring_repo=ScoringRepository(db_session),
        paper_repo=PaperRepository(db_session),
        state_repo=UserPaperStateRepository(db_session),
        category_key=category_key_for(settings.triage_categories),
    )


def get_agent_service(
    db_session: AsyncSession,
    user_id: UUID,
    graph: CompiledStateGraph,
    scoped_paper: ScopedPaper,
) -> AgentService:
    """The paper-scoped chat agent for one request. All tuning comes from `Settings`."""
    settings = get_settings()
    return AgentService(
        llm_client=get_llm_client(),
        search_service=get_search_service(db_session),
        graph=graph,
        scoped_paper=scoped_paper,
        db_session=db_session,
        semantic_scholar_client=get_semantic_scholar_client(),
        paper_repository=PaperRepository(db_session),
        conversation_repo=ConversationRepository(db_session),
        conversation_window=settings.conversation_window,
        guardrail_threshold=settings.guardrail_threshold,
        top_k=settings.default_top_k,
        max_iterations=settings.max_iterations,
        temperature=settings.default_temperature,
        user_id=user_id,
    )
