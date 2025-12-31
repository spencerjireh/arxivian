"""Integration tests for ChunkRepository with real database."""

import pytest

from src.repositories.chunk_repository import ChunkRepository
from src.repositories.paper_repository import PaperRepository
from tests.integration.conftest import make_chunk_data


class TestChunkRepositoryCRUD:
    """Test chunk CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_bulk_chunks(self, db_session, sample_paper_data, sample_embedding):
        """Verify bulk chunk creation with embeddings."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(3)
        ]

        chunks = await chunk_repo.create_bulk(chunks_data)

        assert len(chunks) == 3
        for i, chunk in enumerate(chunks):
            assert chunk.id is not None
            assert chunk.paper_id == paper.id
            assert chunk.chunk_index == i
            assert len(chunk.embedding) == 1024

    @pytest.mark.asyncio
    async def test_create_bulk_empty_list(self, db_session):
        """Verify bulk create handles empty list."""
        chunk_repo = ChunkRepository(session=db_session)

        chunks = await chunk_repo.create_bulk([])
        assert chunks == []

    @pytest.mark.asyncio
    async def test_get_chunks_by_paper_id(self, db_session, sample_paper_data, sample_embedding):
        """Verify retrieving chunks by paper ID returns ordered results."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        # Create chunks out of order
        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, 2, sample_embedding),
            make_chunk_data(paper.id, paper.arxiv_id, 0, sample_embedding),
            make_chunk_data(paper.id, paper.arxiv_id, 1, sample_embedding),
        ]
        await chunk_repo.create_bulk(chunks_data)

        chunks = await chunk_repo.get_by_paper_id(str(paper.id))

        assert len(chunks) == 3
        # Verify ordered by chunk_index
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    @pytest.mark.asyncio
    async def test_get_chunks_by_arxiv_id(self, db_session, sample_paper_data, sample_embedding):
        """Verify retrieving chunks by arXiv ID."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(2)
        ]
        await chunk_repo.create_bulk(chunks_data)

        chunks = await chunk_repo.get_by_arxiv_id(paper.arxiv_id)

        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_delete_chunks_by_paper_id(self, db_session, sample_paper_data, sample_embedding):
        """Verify deleting chunks by paper ID."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(5)
        ]
        await chunk_repo.create_bulk(chunks_data)

        deleted_count = await chunk_repo.delete_by_paper_id(str(paper.id))

        assert deleted_count == 5

        remaining = await chunk_repo.get_by_paper_id(str(paper.id))
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_count_by_paper_id(self, db_session, sample_paper_data, sample_embedding):
        """Verify counting chunks by paper ID."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(3)
        ]
        await chunk_repo.create_bulk(chunks_data)

        count = await chunk_repo.count_by_paper_id(str(paper.id))
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_total(self, db_session, sample_paper_data, sample_embedding):
        """Verify total chunk count."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        initial_count = await chunk_repo.count()

        paper = await paper_repo.create(sample_paper_data)
        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(4)
        ]
        await chunk_repo.create_bulk(chunks_data)

        final_count = await chunk_repo.count()
        assert final_count == initial_count + 4


class TestChunkRepositoryCascade:
    """Test cascade delete behavior."""

    @pytest.mark.asyncio
    async def test_cascade_delete_with_paper(self, db_session, sample_paper_data, sample_embedding):
        """Verify chunks are cascade-deleted when paper is deleted."""
        paper_repo = PaperRepository(session=db_session)
        chunk_repo = ChunkRepository(session=db_session)

        paper = await paper_repo.create(sample_paper_data)

        chunks_data = [
            make_chunk_data(paper.id, paper.arxiv_id, i, sample_embedding) for i in range(3)
        ]
        await chunk_repo.create_bulk(chunks_data)

        assert await chunk_repo.count_by_paper_id(str(paper.id)) == 3

        await paper_repo.delete(str(paper.id))

        assert await chunk_repo.count_by_paper_id(str(paper.id)) == 0
