"""Paper ingestion router."""

from fastapi import APIRouter
from time import time
import tempfile
import os
from pathlib import Path

from src.schemas.ingest import IngestRequest, IngestResponse, PaperError, PaperResult
from src.dependencies import (
    DbSession,
    ArxivClientDep,
    PDFParserDep,
    EmbeddingsClientDep,
    ChunkingServiceDep,
    PaperRepoDep,
    ChunkRepoDep,
)

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_papers(
    request: IngestRequest,
    db: DbSession,
    arxiv_client: ArxivClientDep,
    pdf_parser: PDFParserDep,
    embeddings_client: EmbeddingsClientDep,
    chunking_service: ChunkingServiceDep,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
) -> IngestResponse:
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
        (other params injected via dependencies)

    Returns:
        IngestResponse with processing summary
    """
    start_time = time()

    papers_fetched = 0
    papers_processed = 0
    chunks_created = 0
    errors = []
    paper_results = []

    try:
        # 1. Search arXiv for papers
        papers = await arxiv_client.search_papers(
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
                # Check if exists
                existing = await paper_repo.get_by_arxiv_id(paper_meta.arxiv_id)
                if existing and not request.force_reprocess:
                    # Skip already processed papers
                    continue

                # Download PDF to temp directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    pdf_path = os.path.join(temp_dir, f"{paper_meta.arxiv_id}.pdf")

                    try:
                        await arxiv_client.download_pdf(pdf_url=paper_meta.pdf_url, save_path=pdf_path)
                    except Exception as e:
                        raise Exception(f"PDF download failed: {str(e)}")

                    # Parse PDF
                    try:
                        parsed = await pdf_parser.parse_pdf(pdf_path)
                    except Exception as e:
                        raise Exception(f"PDF parsing failed: {str(e)}")

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
                    paper = await paper_repo.update(existing.id, paper_data)
                    # Delete old chunks
                    await chunk_repo.delete_by_paper_id(existing.id)
                else:
                    paper = await paper_repo.create(paper_data)

                # Chunk text
                chunks = chunking_service.chunk_document(
                    text=parsed.raw_text, sections=parsed.sections
                )

                if not chunks:
                    raise Exception("No chunks created from document")

                # Generate embeddings
                chunk_texts = [c.chunk_text for c in chunks]
                try:
                    embeddings = await embeddings_client.embed_documents(chunk_texts)
                except Exception as e:
                    raise Exception(f"Embedding generation failed: {str(e)}")

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

                await chunk_repo.create_bulk(chunks_data)
                paper_chunks_count = len(chunks_data)
                chunks_created += paper_chunks_count

                papers_processed += 1
                paper_results.append(
                    PaperResult(
                        arxiv_id=paper.arxiv_id,
                        title=paper.title,
                        chunks_created=paper_chunks_count,
                        status="success",
                    )
                )

            except Exception as e:
                # Collect per-paper errors
                errors.append(PaperError(arxiv_id=paper_meta.arxiv_id, error=str(e)))

        # Commit all changes
        await db.commit()

    except Exception as e:
        # Fatal error during search or setup
        await db.rollback()
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
