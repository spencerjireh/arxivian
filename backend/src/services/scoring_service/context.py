"""Context object passed to all scoring-graph nodes (mirrors `AgentContext`).

Holds the dependencies a scoring run needs. Built per-task from a fresh async DB session
(see `factories.service_factories.get_scoring_context`) because the scoring graph is driven
from a Celery worker, not a FastAPI request -- there is no `app.state` to read from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.clients.base_llm_client import BaseLLMClient
from src.clients.semantic_scholar_client import SemanticScholarClient
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.services.ingest_service import IngestService
from src.services.search_service import SearchService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ScoringContext:
    """Dependencies for the Stage 2 scoring graph."""

    def __init__(
        self,
        *,
        llm_client: BaseLLMClient,
        semantic_scholar_client: SemanticScholarClient,
        ingest_service: IngestService,
        search_service: SearchService,
        paper_repository: PaperRepository,
        scoring_repository: ScoringRepository,
        db_session: AsyncSession,
        strong_model: str,
        rubric_version: str,
    ):
        self.llm_client = llm_client
        self.semantic_scholar_client = semantic_scholar_client
        self.ingest_service = ingest_service
        self.search_service = search_service
        self.paper_repository = paper_repository
        self.scoring_repository = scoring_repository
        self.db_session = db_session
        self.strong_model = strong_model
        self.rubric_version = rubric_version
