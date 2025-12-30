"""Tests for IngestService."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sqlalchemy.exc import OperationalError

from src.services.ingest_service import IngestService
from src.schemas.ingest import IngestRequest
from src.exceptions import PDFProcessingError, InsufficientChunksError, EmbeddingServiceError


class TestIngestPapers:
    """Tests for IngestService.ingest_papers method."""

    @pytest.fixture
    def ingest_service(
        self,
        mock_arxiv_client,
        mock_pdf_parser,
        mock_embeddings_client,
        mock_chunking_service,
        mock_paper_repository,
        mock_chunk_repository,
    ):
        return IngestService(
            arxiv_client=mock_arxiv_client,
            pdf_parser=mock_pdf_parser,
            embeddings_client=mock_embeddings_client,
            chunking_service=mock_chunking_service,
            paper_repository=mock_paper_repository,
            chunk_repository=mock_chunk_repository,
        )

    @pytest.mark.asyncio
    async def test_ingest_papers_searches_arxiv(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify arXiv client search is called."""
        mock_arxiv_client.search_papers.return_value = []
        request = IngestRequest(query="machine learning", max_results=5)

        await ingest_service.ingest_papers(request)

        mock_arxiv_client.search_papers.assert_called_once()
        call_kwargs = mock_arxiv_client.search_papers.call_args.kwargs
        assert call_kwargs["query"] == "machine learning"
        assert call_kwargs["max_results"] == 5

    @pytest.mark.asyncio
    async def test_ingest_papers_returns_response_structure(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify IngestResponse structure."""
        mock_arxiv_client.search_papers.return_value = []
        request = IngestRequest(query="test")

        response = await ingest_service.ingest_papers(request)

        assert hasattr(response, "status")
        assert hasattr(response, "papers_fetched")
        assert hasattr(response, "papers_processed")
        assert hasattr(response, "chunks_created")
        assert hasattr(response, "duration_seconds")
        assert hasattr(response, "errors")

    @pytest.mark.asyncio
    async def test_ingest_papers_counts_fetched(
        self, ingest_service, mock_arxiv_client, sample_arxiv_paper
    ):
        """Verify papers_fetched count."""
        mock_arxiv_client.search_papers.return_value = [sample_arxiv_paper, sample_arxiv_paper]
        request = IngestRequest(query="test")

        response = await ingest_service.ingest_papers(request)

        assert response.papers_fetched == 2

    @pytest.mark.asyncio
    async def test_ingest_papers_handles_arxiv_failure(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify failed status on arxiv error."""
        mock_arxiv_client.search_papers.side_effect = Exception("API error")
        request = IngestRequest(query="test")

        response = await ingest_service.ingest_papers(request)

        assert response.status == "failed"
        assert response.papers_fetched == 0
        assert len(response.errors) > 0

    @pytest.mark.asyncio
    async def test_ingest_papers_passes_filters(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify categories, dates are passed to arxiv."""
        mock_arxiv_client.search_papers.return_value = []
        # IngestRequest expects date strings in YYYY-MM-DD format
        request = IngestRequest(
            query="test",
            categories=["cs.LG"],
            start_date="2023-01-01",
            end_date="2023-12-31",
        )

        await ingest_service.ingest_papers(request)

        call_kwargs = mock_arxiv_client.search_papers.call_args.kwargs
        assert call_kwargs["categories"] == ["cs.LG"]
        assert call_kwargs["start_date"] == "2023-01-01"
        assert call_kwargs["end_date"] == "2023-12-31"

    @pytest.mark.asyncio
    async def test_ingest_papers_collects_processing_errors(
        self,
        ingest_service,
        mock_arxiv_client,
        mock_paper_repository,
        sample_arxiv_paper,
    ):
        """Verify errors list is populated on processing failures."""
        mock_arxiv_client.search_papers.return_value = [sample_arxiv_paper]
        mock_paper_repository.get_by_arxiv_id.return_value = None

        # Make download fail
        ingest_service.arxiv_client.download_pdf.side_effect = Exception("Download failed")

        request = IngestRequest(query="test")
        response = await ingest_service.ingest_papers(request)

        assert len(response.errors) == 1
        assert response.errors[0].arxiv_id == sample_arxiv_paper.arxiv_id


class TestIngestByIds:
    """Tests for IngestService.ingest_by_ids method."""

    @pytest.fixture
    def ingest_service(
        self,
        mock_arxiv_client,
        mock_pdf_parser,
        mock_embeddings_client,
        mock_chunking_service,
        mock_paper_repository,
        mock_chunk_repository,
    ):
        return IngestService(
            arxiv_client=mock_arxiv_client,
            pdf_parser=mock_pdf_parser,
            embeddings_client=mock_embeddings_client,
            chunking_service=mock_chunking_service,
            paper_repository=mock_paper_repository,
            chunk_repository=mock_chunk_repository,
        )

    @pytest.mark.asyncio
    async def test_ingest_by_ids_fetches_papers(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify get_papers_by_ids is called."""
        mock_arxiv_client.get_papers_by_ids.return_value = []

        await ingest_service.ingest_by_ids(["2301.00001", "2301.00002"])

        mock_arxiv_client.get_papers_by_ids.assert_called_once_with(
            ["2301.00001", "2301.00002"]
        )

    @pytest.mark.asyncio
    async def test_ingest_by_ids_handles_arxiv_failure(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify errors collected on arxiv failure."""
        mock_arxiv_client.get_papers_by_ids.side_effect = Exception("API error")

        response = await ingest_service.ingest_by_ids(["2301.00001"])

        assert response.status == "failed"
        assert len(response.errors) > 0

    @pytest.mark.asyncio
    async def test_ingest_by_ids_returns_response(
        self, ingest_service, mock_arxiv_client
    ):
        """Verify IngestResponse structure."""
        mock_arxiv_client.get_papers_by_ids.return_value = []

        response = await ingest_service.ingest_by_ids(["2301.00001"])

        assert response.status == "completed"
        assert hasattr(response, "papers_fetched")
        assert hasattr(response, "duration_seconds")


class TestProcessSinglePaper:
    """Tests for IngestService._process_single_paper method."""

    @pytest.fixture
    def ingest_service(
        self,
        mock_arxiv_client,
        mock_pdf_parser,
        mock_embeddings_client,
        mock_chunking_service,
        mock_paper_repository,
        mock_chunk_repository,
    ):
        # Setup session with begin_nested context manager
        @asynccontextmanager
        async def mock_begin_nested():
            yield

        mock_paper_repository.session.begin_nested = mock_begin_nested

        return IngestService(
            arxiv_client=mock_arxiv_client,
            pdf_parser=mock_pdf_parser,
            embeddings_client=mock_embeddings_client,
            chunking_service=mock_chunking_service,
            paper_repository=mock_paper_repository,
            chunk_repository=mock_chunk_repository,
        )

    @pytest.mark.asyncio
    async def test_process_skips_existing_paper(
        self,
        ingest_service,
        mock_paper_repository,
        sample_arxiv_paper,
    ):
        """Verify skip when paper exists and not force_reprocess."""
        existing_paper = Mock()
        mock_paper_repository.get_by_arxiv_id.return_value = existing_paper

        result = await ingest_service._process_single_paper(
            sample_arxiv_paper, force_reprocess=False
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_process_downloads_pdf(
        self,
        ingest_service,
        mock_arxiv_client,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        mock_chunk_repository,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify download_pdf is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_arxiv_client.download_pdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_parses_pdf(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify parse_pdf is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_pdf_parser.parse_pdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chunks_text(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify chunk_document is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_chunking_service.chunk_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_generates_embeddings(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify embed_documents is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_embeddings_client.embed_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_creates_paper_record(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify paper_repository.create is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_paper_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_creates_chunks(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        mock_chunk_repository,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify chunk_repository.create_bulk is called."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_chunk_repository.create_bulk.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_handles_download_failure(
        self,
        ingest_service,
        mock_arxiv_client,
        mock_paper_repository,
        sample_arxiv_paper,
    ):
        """Verify PDFProcessingError raised on download failure."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_arxiv_client.download_pdf.side_effect = Exception("Download failed")

        with pytest.raises(PDFProcessingError):
            await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

    @pytest.mark.asyncio
    async def test_process_handles_empty_chunks(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        sample_arxiv_paper,
        sample_parsed_pdf,
    ):
        """Verify InsufficientChunksError raised when no chunks."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = []  # No chunks

        with pytest.raises(InsufficientChunksError):
            await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

    @pytest.mark.asyncio
    async def test_process_handles_embedding_failure(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify EmbeddingServiceError raised on embedding failure."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.side_effect = Exception("Embedding failed")

        with pytest.raises(EmbeddingServiceError):
            await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

    @pytest.mark.asyncio
    async def test_process_uses_row_locking(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify get_by_arxiv_id_for_update is called for locking."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        await ingest_service._process_single_paper(sample_arxiv_paper, force_reprocess=False)

        mock_paper_repository.get_by_arxiv_id_for_update.assert_called_once_with(
            sample_arxiv_paper.arxiv_id
        )

    @pytest.mark.asyncio
    async def test_process_handles_concurrent_lock(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify OperationalError handling when row locked."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        # Simulate lock failure
        mock_paper_repository.get_by_arxiv_id_for_update.side_effect = OperationalError(
            "could not obtain lock", None, None
        )

        result = await ingest_service._process_single_paper(
            sample_arxiv_paper, force_reprocess=False
        )

        # Should return None when locked by another process
        assert result is None

    @pytest.mark.asyncio
    async def test_process_returns_paper_result(
        self,
        ingest_service,
        mock_paper_repository,
        mock_pdf_parser,
        mock_chunking_service,
        mock_embeddings_client,
        sample_arxiv_paper,
        sample_parsed_pdf,
        sample_chunks,
    ):
        """Verify PaperResult structure is returned."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_paper_repository.get_by_arxiv_id_for_update.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)

        mock_paper = Mock()
        mock_paper.id = "paper-uuid"
        mock_paper.arxiv_id = sample_arxiv_paper.arxiv_id
        mock_paper.title = sample_arxiv_paper.title
        mock_paper_repository.create.return_value = mock_paper

        result = await ingest_service._process_single_paper(
            sample_arxiv_paper, force_reprocess=False
        )

        assert result is not None
        assert result.arxiv_id == sample_arxiv_paper.arxiv_id
        assert result.chunks_created == len(sample_chunks)
        assert result.status == "success"


class TestListPapers:
    """Tests for IngestService.list_papers method."""

    @pytest.fixture
    def ingest_service(
        self,
        mock_arxiv_client,
        mock_pdf_parser,
        mock_embeddings_client,
        mock_chunking_service,
        mock_paper_repository,
        mock_chunk_repository,
    ):
        return IngestService(
            arxiv_client=mock_arxiv_client,
            pdf_parser=mock_pdf_parser,
            embeddings_client=mock_embeddings_client,
            chunking_service=mock_chunking_service,
            paper_repository=mock_paper_repository,
            chunk_repository=mock_chunk_repository,
        )

    @pytest.mark.asyncio
    async def test_list_papers_calls_repository(
        self, ingest_service, mock_paper_repository
    ):
        """Verify get_all is called."""
        mock_paper_repository.get_all.return_value = ([], 0)

        await ingest_service.list_papers()

        mock_paper_repository.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_papers_passes_filters(
        self, ingest_service, mock_paper_repository
    ):
        """Verify query, author, category, dates are passed."""
        mock_paper_repository.get_all.return_value = ([], 0)
        start = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end = datetime(2023, 12, 31, tzinfo=timezone.utc)

        await ingest_service.list_papers(
            query="test",
            author="Smith",
            categories=["cs.LG"],
            start_date=start,
            end_date=end,
            limit=10,
            offset=5,
        )

        call_kwargs = mock_paper_repository.get_all.call_args.kwargs
        assert call_kwargs["query"] == "test"
        assert call_kwargs["author_filter"] == "Smith"
        assert call_kwargs["category_filter"] == "cs.LG"
        assert call_kwargs["start_date"] == start
        assert call_kwargs["end_date"] == end
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    @pytest.mark.asyncio
    async def test_list_papers_returns_tuple(
        self, ingest_service, mock_paper_repository
    ):
        """Verify (papers, total) format."""
        mock_paper_repository.get_all.return_value = ([], 0)

        result = await ingest_service.list_papers()

        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_papers_truncates_abstract(
        self, ingest_service, mock_paper_repository
    ):
        """Verify 500 char limit with '...'."""
        mock_paper = Mock()
        mock_paper.arxiv_id = "2301.00001"
        mock_paper.title = "Test"
        mock_paper.authors = ["Author"]
        mock_paper.abstract = "x" * 600  # Long abstract
        mock_paper.categories = ["cs.LG"]
        mock_paper.published_date = datetime.now(timezone.utc)
        mock_paper.pdf_url = "https://example.com"

        mock_paper_repository.get_all.return_value = ([mock_paper], 1)

        papers, _ = await ingest_service.list_papers()

        assert len(papers[0]["abstract"]) == 503  # 500 + "..."
        assert papers[0]["abstract"].endswith("...")

    @pytest.mark.asyncio
    async def test_list_papers_formats_dates(
        self, ingest_service, mock_paper_repository
    ):
        """Verify ISO format dates."""
        mock_paper = Mock()
        mock_paper.arxiv_id = "2301.00001"
        mock_paper.title = "Test"
        mock_paper.authors = ["Author"]
        mock_paper.abstract = "Abstract"
        mock_paper.categories = ["cs.LG"]
        mock_paper.published_date = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_paper.pdf_url = "https://example.com"

        mock_paper_repository.get_all.return_value = ([mock_paper], 1)

        papers, _ = await ingest_service.list_papers()

        assert "2023-06-15" in papers[0]["published_date"]

    @pytest.mark.asyncio
    async def test_list_papers_handles_first_category(
        self, ingest_service, mock_paper_repository
    ):
        """Verify categories[0] is used for filter."""
        mock_paper_repository.get_all.return_value = ([], 0)

        await ingest_service.list_papers(categories=["cs.LG", "cs.AI", "stat.ML"])

        call_kwargs = mock_paper_repository.get_all.call_args.kwargs
        assert call_kwargs["category_filter"] == "cs.LG"
