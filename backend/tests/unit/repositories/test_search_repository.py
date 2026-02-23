"""Tests for SearchRepository query preparation logic."""

import pytest
from unittest.mock import Mock

from src.repositories.search_repository import SearchRepository


class TestSearchRepositoryQueryPreparation:
    """Tests for query string preparation - actual logic, not mocked CRUD."""

    @pytest.fixture
    def search_repository(self, mock_async_session):
        return SearchRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_fulltext_search_passes_raw_query_to_websearch_tsquery(
        self, search_repository, mock_async_session
    ):
        """Verify raw query is passed to websearch_to_tsquery (no manual tokenisation)."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="machine learning models", top_k=10)

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["query"] == "machine learning models"

    @pytest.mark.asyncio
    async def test_fulltext_search_single_word_unchanged(
        self, search_repository, mock_async_session
    ):
        """Verify single word query is not modified."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        await search_repository.fulltext_search(query="transformers", top_k=10)

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["query"] == "transformers"

    @pytest.mark.asyncio
    async def test_vector_search_formats_embedding_correctly(
        self, search_repository, mock_async_session
    ):
        """Verify embedding is formatted as PostgreSQL vector string."""
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_async_session.execute.return_value = mock_result

        embedding = [0.1, 0.2, 0.3]
        await search_repository.vector_search(
            query_embedding=embedding, top_k=10, min_score=0.0
        )

        call_args = mock_async_session.execute.call_args
        params = call_args[0][1]
        assert params["embedding"] == "[0.1,0.2,0.3]"
