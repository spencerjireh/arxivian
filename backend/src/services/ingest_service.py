"""Service for ingesting papers from arXiv."""

import tempfile
import os
from time import time
from typing import List

from src.schemas.ingest import IngestRequest, IngestResponse, PaperError, PaperResult
from src.clients.arxiv_client import ArxivClient
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.utils.pdf_parser import PDFParser
from src.utils.chunking_service import ChunkingService
from src.repositories.paper_repository import PaperRepository
from src.repositories.chunk_repository import ChunkRepository
from src.exceptions import (
    EmbeddingServiceError,
    InsufficientChunksError,
    PDFProcessingError,
)


class IngestService:
    """Service for paper ingestion orchestration."""

    def __init__(
        self,
        arxiv_client: ArxivClient,
        pdf_parser: PDFParser,
        embeddings_client: JinaEmbeddingsClient,
        chunking_service: ChunkingService,
        paper_repository: PaperRepository,
        chunk_repository: ChunkRepository,
    ):
        """
        Initialize IngestService with dependencies.

        Args:
            arxiv_client: Client for arXiv API interactions
            pdf_parser: Parser for extracting text from PDFs
            embeddings_client: Client for generating embeddings
            chunking_service: Service for chunking documents
            paper_repository: Repository for paper data access
            chunk_repository: Repository for chunk data access
        """
        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser
        self.embeddings_client = embeddings_client
        self.chunking_service = chunking_service
        self.paper_repository = paper_repository
        self.chunk_repository = chunk_repository

    async def ingest_papers(self, request: IngestRequest) -> IngestResponse:
        """
        Ingest papers from arXiv.

        Process:
        1. Search arXiv API for papers
        2. For each paper:
           - Check if exists (skip if not force_reprocess)
           - Download PDF
           - Parse PDF to extract text
           - Chunk text
           - Generate embeddings
           - Store in database
        3. Return summary with counts and errors

        Args:
            request: Ingestion parameters

        Returns:
            IngestResponse with processing summary
        """
        start_time = time()

        papers_fetched = 0
        papers_processed = 0
        chunks_created = 0
        errors: List[PaperError] = []
        paper_results: List[PaperResult] = []

        try:
            # 1. Search arXiv for papers
            papers = await self.arxiv_client.search_papers(
                query=request.query,
                max_results=request.max_results,
                categories=request.categories,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            papers_fetched = len(papers)

            # 2. Process each paper
            for paper_meta in papers:
                try:
                    result = await self._process_single_paper(paper_meta, request.force_reprocess)
                    if result:
                        papers_processed += 1
                        chunks_created += result.chunks_created
                        paper_results.append(result)
                except Exception as e:
                    # Collect per-paper errors
                    errors.append(PaperError(arxiv_id=paper_meta.arxiv_id, error=str(e)))

        except Exception as e:
            # Fatal error during search or setup
            return IngestResponse(
                status="failed",
                papers_fetched=0,
                papers_processed=0,
                chunks_created=0,
                duration_seconds=0,
                errors=[PaperError(arxiv_id="N/A", error=str(e))],
            )

        duration = time() - start_time

        return IngestResponse(
            status="completed",
            papers_fetched=papers_fetched,
            papers_processed=papers_processed,
            chunks_created=chunks_created,
            duration_seconds=duration,
            errors=errors,
            papers=paper_results,
        )

    async def _process_single_paper(self, paper_meta, force_reprocess: bool):
        """
        Process a single paper: download, parse, chunk, and embed.

        Args:
            paper_meta: Paper metadata from arXiv
            force_reprocess: Whether to reprocess existing papers

        Returns:
            PaperResult if processed, None if skipped
        """
        # Check if exists
        existing = await self.paper_repository.get_by_arxiv_id(paper_meta.arxiv_id)
        if existing and not force_reprocess:
            # Skip already processed papers
            return None

        # Download PDF to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, f"{paper_meta.arxiv_id}.pdf")

            try:
                await self.arxiv_client.download_pdf(pdf_url=paper_meta.pdf_url, save_path=pdf_path)
            except Exception as e:
                raise PDFProcessingError(
                    arxiv_id=paper_meta.arxiv_id, stage="download", message=str(e)
                )

            # Parse PDF
            try:
                parsed = await self.pdf_parser.parse_pdf(pdf_path)
            except Exception as e:
                raise PDFProcessingError(
                    arxiv_id=paper_meta.arxiv_id, stage="parsing", message=str(e)
                )

        # Create or update paper record
        paper_data = {
            "arxiv_id": paper_meta.arxiv_id,
            "title": paper_meta.title,
            "authors": paper_meta.authors,
            "abstract": paper_meta.abstract,
            "categories": paper_meta.categories,
            "published_date": paper_meta.published_date,
            "pdf_url": paper_meta.pdf_url,
            "raw_text": parsed.raw_text,
            "sections": parsed.sections,
            "pdf_processed": True,
            "parser_used": "pypdf",
        }

        if existing:
            paper = await self.paper_repository.update(existing.id, paper_data)
            # Delete old chunks
            await self.chunk_repository.delete_by_paper_id(existing.id)
        else:
            paper = await self.paper_repository.create(paper_data)

        # Chunk text
        chunks = self.chunking_service.chunk_document(
            text=parsed.raw_text, sections=parsed.sections
        )

        if not chunks:
            raise InsufficientChunksError(arxiv_id=paper_meta.arxiv_id, chunks_count=0)

        # Generate embeddings
        chunk_texts = [c.chunk_text for c in chunks]
        try:
            embeddings = await self.embeddings_client.embed_documents(chunk_texts)
        except Exception as e:
            raise EmbeddingServiceError(
                message=f"Failed to generate embeddings for {paper_meta.arxiv_id}",
                details={"arxiv_id": paper_meta.arxiv_id, "error": str(e)},
            )

        # Store chunks
        chunks_data = []
        for chunk, embedding in zip(chunks, embeddings):
            chunks_data.append(
                {
                    "paper_id": paper.id,
                    "arxiv_id": paper.arxiv_id,
                    "chunk_text": chunk.chunk_text,
                    "chunk_index": chunk.chunk_index,
                    "section_name": chunk.section_name,
                    "page_number": chunk.page_number,
                    "word_count": chunk.word_count,
                    "embedding": embedding,
                }
            )

        await self.chunk_repository.create_bulk(chunks_data)
        paper_chunks_count = len(chunks_data)

        return PaperResult(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            chunks_created=paper_chunks_count,
            status="success",
        )
