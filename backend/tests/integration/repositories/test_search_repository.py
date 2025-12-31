"""Integration tests for SearchRepository with real pgvector."""

import pytest
import random

from src.repositories.search_repository import SearchRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.chunk_repository import ChunkRepository
from tests.integration.conftest import make_chunk_data


class TestSearchRepositoryVectorSearch:
    """Test vector similarity search with real pgvector."""

    @pytest.fixture
    async def populated_db(self, db_session, sample_paper_data):
        """Populate database with papers and chunks for search tests."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        # Create 2 papers with different content
        paper1_data = {
            **sample_paper_data,
            "arxiv_id": "2301.00001",
            "title": "Deep Learning for Image Recognition",
        }
        paper2_data = {
            **sample_paper_data,
            "arxiv_id": "2301.00002",
            "title": "Natural Language Processing Advances",
        }

        paper1 = await paper_repo.create(paper1_data)
        paper2 = await paper_repo.create(paper2_data)

        # Create embeddings with different patterns
        # Paper 1: embeddings close to [1, 0, 0, ...]
        # Paper 2: embeddings close to [0, 1, 0, ...]
        random.seed(42)

        def make_embedding(base_idx: int):
            emb = [random.uniform(-0.1, 0.1) for _ in range(1024)]
            emb[base_idx] = 0.9
            return emb

        # Paper 1 chunks (position 0 signal)
        chunks1 = [
            {
                **make_chunk_data(paper1.id, paper1.arxiv_id, i, make_embedding(0)),
                "chunk_text": f"Image recognition chunk {i} about convolutional networks",
            }
            for i in range(3)
        ]

        # Paper 2 chunks (position 1 signal)
        chunks2 = [
            {
                **make_chunk_data(paper2.id, paper2.arxiv_id, i, make_embedding(1)),
                "chunk_text": f"NLP chunk {i} about transformer architectures",
            }
            for i in range(3)
        ]

        await chunk_repo.create_bulk(chunks1)
        await chunk_repo.create_bulk(chunks2)

        return {"paper1": paper1, "paper2": paper2}

    @pytest.mark.asyncio
    async def test_vector_search_finds_similar_embeddings(self, db_session, populated_db):
        """Verify vector search returns chunks with similar embeddings."""
        search_repo = SearchRepository(session=db_session)

        # Query embedding similar to paper1 (signal at position 0)
        query_embedding = [0.0] * 1024
        query_embedding[0] = 0.95

        results = await search_repo.vector_search(
            query_embedding=query_embedding,
            top_k=10,
            min_score=0.0,
        )

        assert len(results) > 0
        # Top results should be from paper1
        assert results[0].arxiv_id == "2301.00001"
        assert results[0].score > 0.5

    @pytest.mark.asyncio
    async def test_vector_search_returns_different_paper_for_different_query(
        self, db_session, populated_db
    ):
        """Verify vector search returns correct paper based on embedding similarity."""
        search_repo = SearchRepository(session=db_session)

        # Query embedding similar to paper2 (signal at position 1)
        query_embedding = [0.0] * 1024
        query_embedding[1] = 0.95

        results = await search_repo.vector_search(
            query_embedding=query_embedding,
            top_k=10,
            min_score=0.0,
        )

        assert len(results) > 0
        # Top results should be from paper2
        assert results[0].arxiv_id == "2301.00002"

    @pytest.mark.asyncio
    async def test_vector_search_respects_top_k(self, db_session, populated_db):
        """Verify top_k limits number of results."""
        search_repo = SearchRepository(session=db_session)

        query_embedding = [0.5] * 1024

        results = await search_repo.vector_search(
            query_embedding=query_embedding,
            top_k=2,
            min_score=0.0,
        )

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_vector_search_respects_min_score(self, db_session, populated_db):
        """Verify min_score filters out low-similarity results."""
        search_repo = SearchRepository(session=db_session)

        # Query embedding not similar to anything
        query_embedding = [0.0] * 1024
        query_embedding[500] = 0.95

        results = await search_repo.vector_search(
            query_embedding=query_embedding,
            top_k=10,
            min_score=0.8,
        )

        # All returned results should meet min_score threshold
        for result in results:
            assert result.score >= 0.8

    @pytest.mark.asyncio
    async def test_vector_search_returns_complete_result(self, db_session, populated_db):
        """Verify search results include all expected fields."""
        search_repo = SearchRepository(session=db_session)

        query_embedding = [0.0] * 1024
        query_embedding[0] = 0.95

        results = await search_repo.vector_search(
            query_embedding=query_embedding,
            top_k=1,
            min_score=0.0,
        )

        assert len(results) == 1
        result = results[0]

        assert result.chunk_id is not None
        assert result.paper_id is not None
        assert result.arxiv_id is not None
        assert result.title is not None
        assert result.chunk_text is not None
        assert result.score is not None
        assert result.vector_score is not None


class TestSearchRepositoryFulltextSearch:
    """Test PostgreSQL full-text search."""

    @pytest.fixture
    async def searchable_db(self, db_session, sample_paper_data, sample_embedding):
        """Populate database with searchable content."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            {
                **make_chunk_data(paper.id, paper.arxiv_id, 0, sample_embedding),
                "chunk_text": "Machine learning algorithms for classification tasks",
            },
            {
                **make_chunk_data(paper.id, paper.arxiv_id, 1, sample_embedding),
                "chunk_text": "Neural networks and deep learning architectures",
            },
            {
                **make_chunk_data(paper.id, paper.arxiv_id, 2, sample_embedding),
                "chunk_text": "Statistical analysis and data preprocessing methods",
            },
        ]

        await chunk_repo.create_bulk(chunks_data)

        return paper

    @pytest.mark.asyncio
    async def test_fulltext_search_finds_matching_content(self, db_session, searchable_db):
        """Verify fulltext search finds matching chunks."""
        search_repo = SearchRepository(session=db_session)

        results = await search_repo.fulltext_search(
            query="machine learning",
            top_k=10,
        )

        assert len(results) >= 1
        assert any("learning" in r.chunk_text.lower() for r in results)

    @pytest.mark.asyncio
    async def test_fulltext_search_single_word(self, db_session, searchable_db):
        """Verify fulltext search works with single word."""
        search_repo = SearchRepository(session=db_session)

        results = await search_repo.fulltext_search(
            query="neural",
            top_k=10,
        )

        assert len(results) >= 1
        assert any("neural" in r.chunk_text.lower() for r in results)

    @pytest.mark.asyncio
    async def test_fulltext_search_no_results(self, db_session, searchable_db):
        """Verify fulltext search returns empty for non-matching query."""
        search_repo = SearchRepository(session=db_session)

        results = await search_repo.fulltext_search(
            query="quantum computing blockchain",
            top_k=10,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fulltext_search_respects_top_k(self, db_session, searchable_db):
        """Verify fulltext search respects top_k limit."""
        search_repo = SearchRepository(session=db_session)

        results = await search_repo.fulltext_search(
            query="learning",
            top_k=1,
        )

        assert len(results) <= 1
