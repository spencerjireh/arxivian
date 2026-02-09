"""Tests for IngestService - meaningful logic tests only."""

import uuid
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sqlalchemy.exc import OperationalError

from src.services.ingest_service import IngestService
from src.schemas.ingest import IngestRequest
from src.exceptions import PDFProcessingError, InsufficientChunksError, EmbeddingServiceError

TEST_USER_ID = str(uuid.uuid4())


class TestIngestPapersErrorHandling:
    """Tests for error handling in ingest_papers."""

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
            ingested_by=TEST_USER_ID,
        )

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
        assert "API error" in str(response.errors[0])

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
        ingest_service.arxiv_client.download_pdf.side_effect = Exception("Download failed")

        request = IngestRequest(query="test")
        response = await ingest_service.ingest_papers(request)

        assert len(response.errors) == 1
        assert response.errors[0].arxiv_id == sample_arxiv_paper.arxiv_id


class TestIngestByIds:
    """Tests for ingest_by_ids error handling."""

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
            ingested_by=TEST_USER_ID,
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
        assert "API error" in str(response.errors[0])


class TestProcessSinglePaper:
    """Tests for _process_single_paper business logic."""

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
            ingested_by=TEST_USER_ID,
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
        mock_chunking_service.chunk_document.return_value = []

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
        """Verify OperationalError handling when row locked by another process."""
        mock_paper_repository.get_by_arxiv_id.return_value = None
        mock_pdf_parser.parse_pdf.return_value = sample_parsed_pdf
        mock_chunking_service.chunk_document.return_value = sample_chunks
        mock_embeddings_client.embed_documents.return_value = [[0.1] * 1024] * len(sample_chunks)
        mock_paper_repository.get_by_arxiv_id_for_update.side_effect = OperationalError(
            "could not obtain lock", None, None
        )

        result = await ingest_service._process_single_paper(
            sample_arxiv_paper, force_reprocess=False
        )

        assert result is None


class TestListPapersFormatting:
    """Tests for list_papers response formatting logic."""

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
            ingested_by=TEST_USER_ID,
        )

    @pytest.mark.asyncio
    async def test_list_papers_truncates_abstract(
        self, ingest_service, mock_paper_repository
    ):
        """Verify 500 char limit with '...'."""
        mock_paper = Mock()
        mock_paper.arxiv_id = "2301.00001"
        mock_paper.title = "Test"
        mock_paper.authors = ["Author"]
        mock_paper.abstract = "x" * 600
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
    async def test_list_papers_uses_first_category(
        self, ingest_service, mock_paper_repository
    ):
        """Verify categories[0] is used for filter."""
        mock_paper_repository.get_all.return_value = ([], 0)

        await ingest_service.list_papers(categories=["cs.LG", "cs.AI", "stat.ML"])

        call_kwargs = mock_paper_repository.get_all.call_args.kwargs
        assert call_kwargs["category_filter"] == "cs.LG"
