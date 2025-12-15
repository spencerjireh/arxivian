# Backend Ingestion API Pipeline Explanation

## Overview

The `/ingest` endpoint in `backend/src/routers/ingest.py` provides a comprehensive pipeline for ingesting academic papers from arXiv, processing them, and storing them in a vector database for retrieval. The pipeline follows a clean architecture pattern with clear separation of concerns.

## API Endpoint

**Route**: `POST /ingest`  
**File**: `backend/src/routers/ingest.py:11-38`

The endpoint is simple and delegates all business logic to the `IngestService`:

```python
@router.post("/ingest", response_model=IngestResponse)
async def ingest_papers(
    request: IngestRequest,
    db: DbSession,
    ingest_service: IngestServiceDep,
) -> IngestResponse:
```

### Request Schema (`IngestRequest`)
- **query**: arXiv search query (required)
- **max_results**: Maximum papers to fetch (1-50, default: 10)
- **categories**: arXiv categories filter (optional)
- **start_date/end_date**: Date range filter (optional)
- **force_reprocess**: Whether to reprocess existing papers (default: false)

### Response Schema (`IngestResponse`)
- **status**: "completed" or "failed"
- **papers_fetched**: Number of papers retrieved from arXiv
- **papers_processed**: Number of papers successfully processed
- **chunks_created**: Total text chunks generated
- **duration_seconds**: Processing time
- **errors**: List of per-paper errors
- **papers**: List of processing results per paper
- **Setup**: `just setup`

## Service Layer Architecture

### IngestService (`backend/src/services/ingest_service.py`)

The `IngestService` orchestrates the entire ingestion pipeline with these dependencies:

- **ArxivClient**: Fetches paper metadata and downloads PDFs
- **PDFParser**: Extracts text and structure from PDFs
- **ChunkingService**: Splits documents into searchable chunks
- **EmbeddingsClient**: Generates vector embeddings
- **PaperRepository**: Database operations for paper metadata
- **ChunkRepository**: Database operations for text chunks

## Processing Pipeline

### 1. Paper Discovery (`ingest_service.py:83-90`)
```python
papers = await self.arxiv_client.search_papers(
    query=request.query,
    max_results=request.max_results,
    categories=request.categories,
    start_date=request.start_date,
    end_date=request.end_date,
)
```

The service queries arXiv API to find papers matching the search criteria.

### 2. Individual Paper Processing (`ingest_service.py:127-239`)

For each paper, the pipeline follows these steps:

#### a. Duplicate Check (`ingest_service.py:138-142`)
```python
existing = await self.paper_repository.get_by_arxiv_id(paper_meta.arxiv_id)
if existing and not force_reprocess:
    return None  # Skip already processed papers
```

#### b. PDF Download (`ingest_service.py:144-153`)
- Downloads PDF to temporary directory
- Uses `ArxivClient.download_pdf()`
- Handles download failures with custom exceptions

#### c. PDF Parsing (`ingest_service.py:155-161`)
- Uses `PDFParser.parse_pdf()` to extract text and structure
- Currently uses pypdf as fallback (Docling planned for production)
- Returns `ParsedDocument` with:
  - `raw_text`: Full document text
  - `sections`: Structured sections with page numbers
  - `references`: Extracted citations
  - `metadata`: Parsing information

#### d. Database Storage (`ingest_service.py:163-192`)
- Creates or updates paper record in database
- Stores metadata, raw text, and section information
- Deletes old chunks if reprocessing existing paper

#### e. Text Chunking (`ingest_service.py:193-199`)
- Uses `ChunkingService.chunk_document()` with section awareness
- Default configuration:
  - **target_words**: 600 words per chunk
  - **overlap_words**: 100 words overlap between chunks
  - **min_chunk_words**: 100 words minimum chunk size
- Respects section boundaries when available
- Returns `TextChunk` objects with metadata (section, page, word count)

#### f. Embedding Generation (`ingest_service.py:201-209`)
- Sends chunk texts to `JinaEmbeddingsClient`
- Generates vector embeddings for semantic search
- Handles embedding service failures gracefully

#### g. Chunk Storage (`ingest_service.py:211-239`)
- Bulk inserts chunks with embeddings into database
- Stores chunk metadata:
  - Paper ID and arXiv ID
  - Chunk text and index
  - Section name and page number
  - Word count and embedding vector

## Utility Services

### ChunkingService (`backend/src/utils/chunking_service.py`)

Implements intelligent document chunking:

- **Section-aware chunking**: Respects document structure when available
- **Overlapping chunks**: Ensures context continuity between chunks
- **Size optimization**: Skips chunks that are too small (except final chunks)
- **Metadata preservation**: Maintains section and page information

### PDFParser (`backend/src/utils/pdf_parser.py`)

Handles PDF text extraction:

- **Async processing**: Runs blocking operations in thread pool
- **Structure extraction**: Identifies sections and page boundaries
- **Reference detection**: Extracts citation information
- **Error handling**: Graceful fallback on parsing failures
- **Production-ready**: Designed to integrate with Docling for advanced parsing

## Dependency Injection

The system uses FastAPI's dependency injection:

- **Service factories** (`backend/src/factories/service_factories.py`): Create service instances with proper dependencies
- **Client factories** (`backend/src/factories/client_factories.py`): Manage singleton clients
- **Repository dependencies** (`backend/src/dependencies.py`): Request-scoped database access

## Error Handling

The pipeline implements comprehensive error handling:

- **Per-paper errors**: Collected and returned without stopping the entire process
- **Custom exceptions**: Specific error types for different failure modes:
  - `PDFProcessingError`: Download/parsing failures
  - `EmbeddingServiceError`: Embedding generation failures
  - `InsufficientChunksError`: Too few chunks generated
- **Transaction management**: Explicit commit after successful processing

## Performance Considerations

- **Async operations**: All I/O operations are asynchronous
- **Bulk operations**: Chunks are inserted in bulk for efficiency
- **Temporary files**: PDFs are cleaned up automatically
- **Singleton clients**: Reused across requests for efficiency
- **Configurable limits**: Prevents resource exhaustion

## Database Schema

The pipeline stores data in two main tables:

- **papers**: Paper metadata, raw text, and structure
- **chunks**: Text chunks with embeddings for vector search

This architecture enables efficient semantic search and retrieval for the agent system.
