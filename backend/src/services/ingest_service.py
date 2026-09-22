"""Service for ingesting papers from arXiv."""

import tempfile
from pathlib import Path
from time import time
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

from src.clients.arxiv_client import ArxivClient, ArxivPaper
from src.clients.embeddings_client import EmbeddingsClient
from src.exceptions import (
    EmbeddingServiceError,
    InsufficientChunksError,
    PDFProcessingError,
)
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.paper_repository import PaperRepository
from src.services.chunking_service import ChunkingService
from src.utils.logger import get_logger
from src.utils.pdf_parser import PDFParser

log = get_logger(__name__)


class IngestRequest(BaseModel):
    """Request to ingest papers from arXiv."""

    query: str = Field(..., description="arXiv search query")
    max_results: int = Field(10, ge=1, le=50, description="Maximum papers to fetch")
    categories: list[str] | None = Field(None, description="arXiv categories filter")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")
    force_reprocess: bool = Field(False, description="Re-process existing papers")
    idempotency_key: str | None = Field(
        default=None,
        description="Unique key to prevent duplicate processing. If provided, duplicate requests return cached response.",
        max_length=64,
    )


class PaperError(BaseModel):
    """Error information for a failed paper."""

    arxiv_id: str
    error: str


class PaperResult(BaseModel):
    """Result for a single paper."""

    arxiv_id: str
    title: str
    chunks_created: int
    status: Literal["success", "failed"]


class IngestResponse(BaseModel):
    """Response from paper ingestion."""

    status: Literal["completed", "failed"]
    papers_fetched: int
    papers_processed: int
    chunks_created: int
    duration_seconds: float
    errors: list[PaperError] = []
    papers: list[PaperResult] = []


class IngestService:
    """Service for paper ingestion orchestration."""

    def __init__(
        self,
        arxiv_client: ArxivClient,
        pdf_parser: PDFParser,
        embeddings_client: EmbeddingsClient,
        chunking_service: ChunkingService,
        paper_repository: PaperRepository,
        chunk_repository: ChunkRepository,
        ingested_by: str | None = None,
    ):
        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser
        self.embeddings_client = embeddings_client
        self.chunking_service = chunking_service
        self.paper_repository = paper_repository
        self.chunk_repository = chunk_repository
        self.ingested_by = ingested_by

    async def ingest_papers(self, request: IngestRequest) -> IngestResponse:
        """
        Ingest papers from arXiv.

        Process:
        1. Search arXiv API for papers
        2. For each paper: download, parse, chunk, embed, store
        3. Return summary with counts and errors
        """
        start_time = time()
        log.info(
            "ingest started",
            query=request.query,
            max_results=request.max_results,
            categories=request.categories,
            force_reprocess=request.force_reprocess,
        )

        papers_fetched = 0
        papers_processed = 0
        chunks_created = 0
        errors: list[PaperError] = []
        paper_results: list[PaperResult] = []

        try:
            # Search arXiv for papers
            papers = await self.arxiv_client.search_papers(
                query=request.query,
                max_results=request.max_results,
                categories=request.categories,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            papers_fetched = len(papers)
            log.info("arxiv search complete", papers_found=papers_fetched)

            # Process each paper
            for paper_meta in papers:
                try:
                    result = await self._process_single_paper(paper_meta, request.force_reprocess)
                    if result:
                        papers_processed += 1
                        chunks_created += result.chunks_created
                        paper_results.append(result)
                except Exception as e:
                    log.warning(
                        "paper processing failed",
                        arxiv_id=paper_meta.arxiv_id,
                        error=str(e),
                    )
                    errors.append(PaperError(arxiv_id=paper_meta.arxiv_id, error=str(e)))

        except Exception as e:
            log.error("ingest failed", error=str(e))
            return IngestResponse(
                status="failed",
                papers_fetched=0,
                papers_processed=0,
                chunks_created=0,
                duration_seconds=0,
                errors=[PaperError(arxiv_id="N/A", error=str(e))],
            )

        duration = time() - start_time
        log.info(
            "ingest complete",
            papers_fetched=papers_fetched,
            papers_processed=papers_processed,
            chunks_created=chunks_created,
            errors=len(errors),
            duration_s=round(duration, 2),
        )

        return IngestResponse(
            status="completed",
            papers_fetched=papers_fetched,
            papers_processed=papers_processed,
            chunks_created=chunks_created,
            duration_seconds=duration,
            errors=errors,
            papers=paper_results,
        )

    async def _process_single_paper(
        self, paper_meta: ArxivPaper, force_reprocess: bool
    ) -> PaperResult | None:
        """
        Process a single paper: download, parse, chunk, and embed.

        All database operations are wrapped in a savepoint transaction that
        rolls back on any failure, preventing orphaned records. Uses row-level
        locking to prevent race conditions with concurrent ingestion requests.
        """
        arxiv_id = paper_meta.arxiv_id
        session = self.paper_repository.session

        # Quick check if paper already exists globally (read-only, outside transaction)
        existing = await self.paper_repository.get_by_arxiv_id(arxiv_id)
        if existing and not force_reprocess:
            log.debug("paper skipped (exists)", arxiv_id=arxiv_id)
            return None

        log.info("processing paper", arxiv_id=arxiv_id, title=paper_meta.title[:80])

        # Download and parse PDF (outside transaction - no DB operations)
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = str(Path(temp_dir) / f"{arxiv_id}.pdf")

            if not paper_meta.pdf_url:
                raise PDFProcessingError(arxiv_id=arxiv_id, stage="download", message="No PDF URL")

            try:
                await self.arxiv_client.download_pdf(pdf_url=paper_meta.pdf_url, save_path=pdf_path)
                log.debug("pdf downloaded", arxiv_id=arxiv_id)
            except Exception as e:
                raise PDFProcessingError(arxiv_id=arxiv_id, stage="download", message=str(e)) from e

            # Parse PDF (now raises PDFProcessingError on failure)
            parsed = await self.pdf_parser.parse_pdf(pdf_path, arxiv_id=arxiv_id)
            log.debug(
                "pdf parsed",
                arxiv_id=arxiv_id,
                text_len=len(parsed.raw_text),
                sections=len(parsed.sections),
            )

        # Chunk text (outside transaction - no DB operations)
        chunks = self.chunking_service.chunk_document(
            text=parsed.raw_text, sections=parsed.sections
        )

        if not chunks:
            raise InsufficientChunksError(arxiv_id=arxiv_id, chunks_count=0)

        log.debug("text chunked", arxiv_id=arxiv_id, chunks=len(chunks))

        # Generate embeddings (outside transaction - external service call)
        chunk_texts = [c.text for c in chunks]
        try:
            embeddings = await self.embeddings_client.embed_documents(chunk_texts)
            log.debug("embeddings generated", arxiv_id=arxiv_id, count=len(embeddings))
        except Exception as e:
            raise EmbeddingServiceError(
                message=f"Failed to generate embeddings for {arxiv_id}",
                details={"arxiv_id": arxiv_id, "error": str(e)},
            ) from e

        # Database operations wrapped in savepoint for atomic rollback
        async with session.begin_nested():
            # Re-check with locking to prevent race conditions
            try:
                existing_locked = await self.paper_repository.get_by_arxiv_id_for_update(arxiv_id)
            except OperationalError:
                # Another transaction has this paper locked - skip
                log.info("paper being processed by another request", arxiv_id=arxiv_id)
                return None

            # Double-check after acquiring lock (another request may have just finished)
            if existing_locked and not force_reprocess:
                log.debug("paper skipped (exists after lock)", arxiv_id=arxiv_id)
                return None

            # Create or update paper record
            paper_data = {
                "arxiv_id": arxiv_id,
                "ingested_by": self.ingested_by,
                "title": paper_meta.title,
                "authors": paper_meta.authors,
                "abstract": paper_meta.abstract,
                "categories": paper_meta.categories,
                "published_date": paper_meta.published_date,
                "pdf_url": paper_meta.pdf_url,
                "raw_text": parsed.raw_text,
                "sections": parsed.sections,
                "references": parsed.references or None,
                "pdf_processed": True,
                "parser_used": "pypdf",
            }

            if existing_locked:
                existing_id = str(existing_locked.id)
                paper = await self.paper_repository.update(existing_id, paper_data)
                await self.chunk_repository.delete_by_paper_id(existing_id)
                log.debug("paper updated", arxiv_id=arxiv_id)
            else:
                paper = await self.paper_repository.create(paper_data)
                log.debug("paper created", arxiv_id=arxiv_id)

            if not paper:
                raise PDFProcessingError(
                    arxiv_id=arxiv_id,
                    stage="database_save",
                    message="Failed to create or update paper record",
                )

            # Store chunks
            paper_id = str(paper.id)
            paper_arxiv_id = str(paper.arxiv_id)
            paper_title = str(paper.title)

            chunks_data = []
            for chunk, embedding in zip(chunks, embeddings, strict=False):
                chunks_data.append(
                    {
                        "paper_id": paper_id,
                        "arxiv_id": paper_arxiv_id,
                        "chunk_text": chunk.text,
                        "chunk_index": chunk.chunk_index,
                        "section_name": chunk.section_name,
                        "page_number": chunk.page_number,
                        "word_count": chunk.word_count,
                        "embedding": embedding,
                    }
                )

            await self.chunk_repository.create_bulk(chunks_data)
            # Savepoint commits automatically on successful exit

        log.info("paper processed", arxiv_id=arxiv_id, chunks=len(chunks_data))

        return PaperResult(
            arxiv_id=paper_arxiv_id,
            title=paper_title,
            chunks_created=len(chunks_data),
            status="success",
        )

    async def ingest_by_ids(
        self, arxiv_ids: list[str], force_reprocess: bool = False
    ) -> IngestResponse:
        """
        Ingest specific papers by arXiv ID.

        Args:
            arxiv_ids: List of arXiv paper IDs
            force_reprocess: Re-process existing papers

        Returns:
            IngestResponse with processing summary
        """
        start_time = time()
        log.info("ingest by ids started", count=len(arxiv_ids), force_reprocess=force_reprocess)

        papers_fetched = 0
        papers_processed = 0
        chunks_created = 0
        errors: list[PaperError] = []
        paper_results: list[PaperResult] = []

        try:
            papers = await self.arxiv_client.get_papers_by_ids(arxiv_ids)
            papers_fetched = len(papers)

            for paper_meta in papers:
                try:
                    result = await self._process_single_paper(paper_meta, force_reprocess)
                    if result:
                        papers_processed += 1
                        chunks_created += result.chunks_created
                        paper_results.append(result)
                except Exception as e:
                    log.warning(
                        "paper processing failed",
                        arxiv_id=paper_meta.arxiv_id,
                        error=str(e),
                    )
                    errors.append(PaperError(arxiv_id=paper_meta.arxiv_id, error=str(e)))

        except Exception as e:
            log.error("ingest by ids failed", error=str(e))
            return IngestResponse(
                status="failed",
                papers_fetched=0,
                papers_processed=0,
                chunks_created=0,
                duration_seconds=0,
                errors=[PaperError(arxiv_id="N/A", error=str(e))],
            )

        duration = time() - start_time
        log.info(
            "ingest by ids complete",
            papers_fetched=papers_fetched,
            papers_processed=papers_processed,
            chunks_created=chunks_created,
            errors=len(errors),
            duration_s=round(duration, 2),
        )

        return IngestResponse(
            status="completed",
            papers_fetched=papers_fetched,
            papers_processed=papers_processed,
            chunks_created=chunks_created,
            duration_seconds=duration,
            errors=errors,
            papers=paper_results,
        )
