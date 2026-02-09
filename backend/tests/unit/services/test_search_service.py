"""Tests for SearchService."""

import pytest

from src.services.search_service import SearchService
from src.repositories.search_repository import SearchResult


def create_search_result(chunk_id: str, score: float = 0.9, **kwargs) -> SearchResult:
    """Helper to create SearchResult objects for testing."""
    defaults = {
        "chunk_id": chunk_id,
        "paper_id": "paper-1",
        "arxiv_id": "2301.00001",
        "title": "Test Paper",
        "authors": ["Author One"],
        "chunk_text": f"Chunk text for {chunk_id}",
        "section_name": "Introduction",
        "page_number": 1,
        "score": score,
        "vector_score": score if "vector_score" not in kwargs else kwargs.get("vector_score"),
        "text_score": kwargs.get("text_score"),
        "published_date": "2023-01-01",
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
    }
    defaults.update(kwargs)
    return SearchResult(**defaults)


class TestSearchServiceHybridSearch:
    """Tests for SearchService.hybrid_search method - mode routing."""

    @pytest.fixture
    def search_service(self, mock_search_repository, mock_embeddings_client):
        return SearchService(
            search_repository=mock_search_repository,
            embeddings_client=mock_embeddings_client,
            rrf_k=60,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_vector_mode_calls_vector_only(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify mode='vector' routes to _vector_only_search."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []

        await search_service.hybrid_search("test query", top_k=5, mode="vector")

        mock_embeddings_client.embed_query.assert_called_once_with("test query")
        mock_search_repository.vector_search.assert_called_once()
        mock_search_repository.fulltext_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_hybrid_search_fulltext_mode_calls_fulltext_only(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify mode='fulltext' routes to _fulltext_only_search."""
        mock_search_repository.fulltext_search.return_value = []

        await search_service.hybrid_search("test query", top_k=5, mode="fulltext")

        mock_search_repository.fulltext_search.assert_called_once()
        mock_embeddings_client.embed_query.assert_not_called()
        mock_search_repository.vector_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_hybrid_search_hybrid_mode_calls_rrf(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify default mode uses RRF fusion (calls both searches)."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []
        mock_search_repository.fulltext_search.return_value = []

        await search_service.hybrid_search("test query", top_k=5, mode="hybrid")

        mock_embeddings_client.embed_query.assert_called_once()
        mock_search_repository.vector_search.assert_called_once()
        mock_search_repository.fulltext_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify results are returned from search."""
        expected_result = create_search_result("chunk-1")
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = [expected_result]

        results = await search_service.hybrid_search("test", top_k=5, mode="vector")

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_top_k(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify top_k parameter is passed through."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []

        await search_service.hybrid_search("test", top_k=15, mode="vector")

        call_kwargs = mock_search_repository.vector_search.call_args.kwargs
        assert call_kwargs["top_k"] == 15

    @pytest.mark.asyncio
    async def test_hybrid_search_respects_min_score(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify min_score is passed to vector search."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []

        await search_service.hybrid_search("test", top_k=5, mode="vector", min_score=0.5)

        call_kwargs = mock_search_repository.vector_search.call_args.kwargs
        assert call_kwargs["min_score"] == 0.5


class TestSearchServiceVectorSearch:
    """Tests for SearchService._vector_only_search method."""

    @pytest.fixture
    def search_service(self, mock_search_repository, mock_embeddings_client):
        return SearchService(
            search_repository=mock_search_repository,
            embeddings_client=mock_embeddings_client,
        )

    @pytest.mark.asyncio
    async def test_vector_only_search_embeds_query(
        self, search_service, mock_embeddings_client, mock_search_repository
    ):
        """Verify embeddings client is called with query."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []

        await search_service._vector_only_search("machine learning", top_k=5, min_score=0.0)

        mock_embeddings_client.embed_query.assert_called_once_with("machine learning")

    @pytest.mark.asyncio
    async def test_vector_only_search_calls_repository(
        self, search_service, mock_embeddings_client, mock_search_repository
    ):
        """Verify search repository is called."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []

        await search_service._vector_only_search("test", top_k=10, min_score=0.3)

        mock_search_repository.vector_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_only_search_passes_embedding(
        self, search_service, mock_embeddings_client, mock_search_repository
    ):
        """Verify embedding is passed to repository."""
        embedding = [0.5] * 1024
        mock_embeddings_client.embed_query.return_value = embedding
        mock_search_repository.vector_search.return_value = []

        await search_service._vector_only_search("test", top_k=5, min_score=0.0)

        call_kwargs = mock_search_repository.vector_search.call_args.kwargs
        assert call_kwargs["query_embedding"] == embedding

class TestSearchServiceFulltextSearch:
    """Tests for SearchService._fulltext_only_search method."""

    @pytest.fixture
    def search_service(self, mock_search_repository, mock_embeddings_client):
        return SearchService(
            search_repository=mock_search_repository,
            embeddings_client=mock_embeddings_client,
        )

    @pytest.mark.asyncio
    async def test_fulltext_only_search_calls_repository(
        self, search_service, mock_search_repository
    ):
        """Verify repository method called."""
        mock_search_repository.fulltext_search.return_value = []

        await search_service._fulltext_only_search("neural networks", top_k=10)

        mock_search_repository.fulltext_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_fulltext_only_search_passes_query(
        self, search_service, mock_search_repository
    ):
        """Verify query is passed correctly."""
        mock_search_repository.fulltext_search.return_value = []

        await search_service._fulltext_only_search("deep learning", top_k=5)

        call_kwargs = mock_search_repository.fulltext_search.call_args.kwargs
        assert call_kwargs["query"] == "deep learning"
        assert call_kwargs["top_k"] == 5

class TestSearchServiceRRF:
    """Tests for SearchService RRF (Reciprocal Rank Fusion) implementation."""

    @pytest.fixture
    def search_service(self, mock_search_repository, mock_embeddings_client):
        return SearchService(
            search_repository=mock_search_repository,
            embeddings_client=mock_embeddings_client,
            rrf_k=60,
        )

    @pytest.mark.asyncio
    async def test_rrf_fetches_double_top_k(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify fetch_k = top_k * 2."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []
        mock_search_repository.fulltext_search.return_value = []

        await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        vector_call = mock_search_repository.vector_search.call_args.kwargs
        fulltext_call = mock_search_repository.fulltext_search.call_args.kwargs
        assert vector_call["top_k"] == 10  # 5 * 2
        assert fulltext_call["top_k"] == 10  # 5 * 2

    @pytest.mark.asyncio
    async def test_rrf_combines_vector_and_fulltext(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify both searches are called."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []
        mock_search_repository.fulltext_search.return_value = []

        await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        mock_search_repository.vector_search.assert_called_once()
        mock_search_repository.fulltext_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_rrf_deduplicates_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify same chunk_id only appears once."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024

        # Same chunk appears in both searches
        vector_result = create_search_result("chunk-1", score=0.9)
        fulltext_result = create_search_result("chunk-1", score=0.8)

        mock_search_repository.vector_search.return_value = [vector_result]
        mock_search_repository.fulltext_search.return_value = [fulltext_result]

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        # Should only have one result for chunk-1
        chunk_ids = [r.chunk_id for r in results]
        assert chunk_ids.count("chunk-1") == 1

    @pytest.mark.asyncio
    async def test_rrf_scores_correctly(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify RRF formula: 1/(rank + k)."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024

        # Chunk appears in both searches at rank 0
        vector_result = create_search_result("chunk-1")
        fulltext_result = create_search_result("chunk-1")

        mock_search_repository.vector_search.return_value = [vector_result]
        mock_search_repository.fulltext_search.return_value = [fulltext_result]

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        # RRF score for rank 0 in both = 1/(0+60) + 1/(0+60) = 2/60
        # Then normalized by dividing by (2/60) -> score = 1.0
        assert len(results) == 1
        # Score should be normalized
        assert results[0].score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_rrf_orders_by_combined_score(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify results sorted by RRF score descending."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024

        # chunk-1 appears in both (high score), chunk-2 only in vector (lower score)
        vector_results = [
            create_search_result("chunk-1"),
            create_search_result("chunk-2"),
        ]
        fulltext_results = [
            create_search_result("chunk-1"),
        ]

        mock_search_repository.vector_search.return_value = vector_results
        mock_search_repository.fulltext_search.return_value = fulltext_results

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        # chunk-1 should rank higher (appears in both)
        assert len(results) == 2
        assert results[0].chunk_id == "chunk-1"
        assert results[1].chunk_id == "chunk-2"

    @pytest.mark.asyncio
    async def test_rrf_returns_top_k_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify output limited to top_k."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024

        # Create more results than top_k
        vector_results = [create_search_result(f"chunk-{i}") for i in range(10)]
        fulltext_results = [create_search_result(f"chunk-{i+10}") for i in range(10)]

        mock_search_repository.vector_search.return_value = vector_results
        mock_search_repository.fulltext_search.return_value = fulltext_results

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_rrf_handles_no_vector_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify works with only fulltext results."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []
        mock_search_repository.fulltext_search.return_value = [create_search_result("chunk-1")]

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"

    @pytest.mark.asyncio
    async def test_rrf_handles_no_fulltext_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify works with only vector results."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = [create_search_result("chunk-1")]
        mock_search_repository.fulltext_search.return_value = []

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"

    @pytest.mark.asyncio
    async def test_rrf_handles_no_results(
        self, search_service, mock_search_repository, mock_embeddings_client
    ):
        """Verify empty list when no matches."""
        mock_embeddings_client.embed_query.return_value = [0.1] * 1024
        mock_search_repository.vector_search.return_value = []
        mock_search_repository.fulltext_search.return_value = []

        results = await search_service._hybrid_search_rrf("test", top_k=5, min_score=0.0)

        assert results == []

    def test_reciprocal_rank_fusion_preserves_metadata(
        self, search_service
    ):
        """Verify result metadata is preserved through fusion."""
        result = create_search_result(
            "chunk-1",
            title="Special Paper",
            authors=["Special Author"],
            section_name="Methods",
        )

        fused = search_service._reciprocal_rank_fusion(
            vector_results=[result],
            fulltext_results=[],
            top_k=5,
        )

        assert len(fused) == 1
        assert fused[0].title == "Special Paper"
        assert fused[0].authors == ["Special Author"]
        assert fused[0].section_name == "Methods"
