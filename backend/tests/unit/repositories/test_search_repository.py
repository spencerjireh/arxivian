"""Tests for SearchRepository."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from src.repositories.search_repository import SearchRepository, SearchResult


def create_mock_db_row(**kwargs):
    """Create a mock database row object."""
    row = Mock()
    defaults = {
        "chunk_id": uuid.uuid4(),
        "paper_id": uuid.uuid4(),
        "arxiv_id": "2301.00001",
        "title": "Test Paper",
        "authors": ["Author One"],
        "chunk_text": "Test chunk content.",
        "section_name": "Introduction",
        "page_number": 1,
        "score": 0.9,
        "published_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
    }
    defaults.update(kwargs)
    for key, value in defaults.items():
        setattr(row, key, value)
    return row


class TestSearchRepositoryVectorSearch:
    """Tests for SearchRepository.vector_search method."""

    @pytest.fixture
    def search_repository(self, mock_async_session):
        return SearchRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_vector_search_executes_query(
        self, search_repository, mock_async_session
    ):
        """Verify SQL is executed."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.vector_search(
            query_embedding=[0.1] * 1024, top_k=10, min_score=0.0
        )

        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_formats_embedding(
        self, search_repository, mock_async_session
    ):
        """Verify embedding string format."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        embedding = [0.1, 0.2, 0.3]
        await search_repository.vector_search(
            query_embedding=embedding, top_k=10, min_score=0.0
        )

        # Check that execute was called with proper parameters
        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]  # Second argument to execute is params dict
        assert "embedding" in params
        assert params["embedding"] == "[0.1,0.2,0.3]"

    @pytest.mark.asyncio
    async def test_vector_search_applies_min_score(
        self, search_repository, mock_async_session
    ):
        """Verify min_score parameter is passed."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.vector_search(
            query_embedding=[0.1] * 10, top_k=10, min_score=0.5
        )

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["min_score"] == 0.5

    @pytest.mark.asyncio
    async def test_vector_search_respects_top_k(
        self, search_repository, mock_async_session
    ):
        """Verify LIMIT is set."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.vector_search(
            query_embedding=[0.1] * 10, top_k=25, min_score=0.0
        )

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["limit"] == 25

    @pytest.mark.asyncio
    async def test_vector_search_returns_search_results(
        self, search_repository, mock_async_session
    ):
        """Verify SearchResult objects are returned."""
        mock_row = create_mock_db_row(score=0.95)
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.vector_search(
            query_embedding=[0.1] * 10, top_k=10, min_score=0.0
        )

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)

    @pytest.mark.asyncio
    async def test_vector_search_populates_all_fields(
        self, search_repository, mock_async_session
    ):
        """Verify all fields are mapped correctly."""
        mock_row = create_mock_db_row(
            chunk_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            arxiv_id="2301.99999",
            title="Special Paper",
            score=0.88,
        )
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.vector_search(
            query_embedding=[0.1] * 10, top_k=10, min_score=0.0
        )

        assert results[0].chunk_id == "12345678-1234-5678-1234-567812345678"
        assert results[0].arxiv_id == "2301.99999"
        assert results[0].title == "Special Paper"
        assert results[0].score == 0.88
        assert results[0].vector_score == 0.88

    @pytest.mark.asyncio
    async def test_vector_search_handles_empty_results(
        self, search_repository, mock_async_session
    ):
        """Verify empty list handling."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.vector_search(
            query_embedding=[0.1] * 10, top_k=10, min_score=0.0
        )

        assert results == []


class TestSearchRepositoryFulltextSearch:
    """Tests for SearchRepository.fulltext_search method."""

    @pytest.fixture
    def search_repository(self, mock_async_session):
        return SearchRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_fulltext_search_executes_query(
        self, search_repository, mock_async_session
    ):
        """Verify SQL is executed."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="machine learning", top_k=10)

        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_fulltext_search_prepares_query(
        self, search_repository, mock_async_session
    ):
        """Verify ' & ' joining for tsquery."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="machine learning", top_k=10)

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        # Query should be joined with " & " for PostgreSQL tsquery
        assert params["query"] == "machine & learning"

    @pytest.mark.asyncio
    async def test_fulltext_search_respects_top_k(
        self, search_repository, mock_async_session
    ):
        """Verify LIMIT is set."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="test", top_k=15)

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["limit"] == 15

    @pytest.mark.asyncio
    async def test_fulltext_search_returns_search_results(
        self, search_repository, mock_async_session
    ):
        """Verify SearchResult objects are returned."""
        mock_row = create_mock_db_row(score=0.75)
        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.fulltext_search(query="test", top_k=10)

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].text_score == 0.75

    @pytest.mark.asyncio
    async def test_fulltext_search_handles_empty_results(
        self, search_repository, mock_async_session
    ):
        """Verify empty list handling."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.fulltext_search(query="nonexistent", top_k=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_fulltext_search_single_word_query(
        self, search_repository, mock_async_session
    ):
        """Verify single word query handling."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="transformers", top_k=10)

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["query"] == "transformers"

    @pytest.mark.asyncio
    async def test_fulltext_search_multiple_results(
        self, search_repository, mock_async_session
    ):
        """Verify multiple results are returned."""
        mock_rows = [
            create_mock_db_row(arxiv_id="2301.00001", score=0.9),
            create_mock_db_row(arxiv_id="2301.00002", score=0.8),
            create_mock_db_row(arxiv_id="2301.00003", score=0.7),
        ]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_async_session.execute.return_value = mock_result

        results = await search_repository.fulltext_search(query="test", top_k=10)

        assert len(results) == 3
        assert results[0].arxiv_id == "2301.00001"
        assert results[1].arxiv_id == "2301.00002"
        assert results[2].arxiv_id == "2301.00003"
