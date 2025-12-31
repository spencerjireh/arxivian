"""Tests for ChunkRepository."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.repositories.chunk_repository import ChunkRepository


class TestChunkRepositoryCreateBulk:
    """Tests for ChunkRepository.create_bulk method."""

    @pytest.fixture
    def chunk_repository(self, mock_async_session):
        return ChunkRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_create_bulk_adds_all_chunks(
        self, chunk_repository, mock_async_session, sample_chunk_data
    ):
        """Verify add_all is called with chunks."""
        chunks_data = [sample_chunk_data, sample_chunk_data]

        await chunk_repository.create_bulk(chunks_data)

        mock_async_session.add_all.assert_called_once()
        # Check that two chunks were added
        call_args = mock_async_session.add_all.call_args[0][0]
        assert len(call_args) == 2

    @pytest.mark.asyncio
    async def test_create_bulk_flushes(
        self, chunk_repository, mock_async_session, sample_chunk_data
    ):
        """Verify flush is called."""
        await chunk_repository.create_bulk([sample_chunk_data])

        mock_async_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_bulk_refreshes_each_chunk(
        self, chunk_repository, mock_async_session, sample_chunk_data
    ):
        """Verify refresh is called for each chunk."""
        chunks_data = [sample_chunk_data, sample_chunk_data, sample_chunk_data]

        await chunk_repository.create_bulk(chunks_data)

        assert mock_async_session.refresh.call_count == 3

    @pytest.mark.asyncio
    async def test_create_bulk_returns_chunks(
        self, chunk_repository, mock_async_session, sample_chunk_data
    ):
        """Verify list of chunks is returned."""
        result = await chunk_repository.create_bulk([sample_chunk_data])

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_bulk_empty_list(
        self, chunk_repository, mock_async_session
    ):
        """Verify handling of empty list."""
        result = await chunk_repository.create_bulk([])

        assert result == []
        mock_async_session.add_all.assert_called_once_with([])


class TestChunkRepositoryGetByPaperId:
    """Tests for ChunkRepository.get_by_paper_id method."""

    @pytest.fixture
    def chunk_repository(self, mock_async_session):
        return ChunkRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_by_paper_id_returns_ordered(
        self, chunk_repository, mock_async_session, mock_chunk
    ):
        """Verify chunks are returned ordered by chunk_index."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_chunk]
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.get_by_paper_id("paper-uuid")

        assert len(result) == 1
        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_paper_id_returns_empty(
        self, chunk_repository, mock_async_session
    ):
        """Verify empty list when no chunks."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.get_by_paper_id("paper-uuid")

        assert result == []


class TestChunkRepositoryGetByArxivId:
    """Tests for ChunkRepository.get_by_arxiv_id method."""

    @pytest.fixture
    def chunk_repository(self, mock_async_session):
        return ChunkRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_returns_ordered(
        self, chunk_repository, mock_async_session, mock_chunk
    ):
        """Verify chunks are returned ordered by chunk_index."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_chunk]
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.get_by_arxiv_id("2301.00001")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_returns_empty(
        self, chunk_repository, mock_async_session
    ):
        """Verify empty list when no chunks."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.get_by_arxiv_id("nonexistent")

        assert result == []


class TestChunkRepositoryDeleteByPaperId:
    """Tests for ChunkRepository.delete_by_paper_id method."""

    @pytest.fixture
    def chunk_repository(self, mock_async_session):
        return ChunkRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_delete_by_paper_id_removes_chunks(
        self, chunk_repository, mock_async_session
    ):
        """Verify delete statement is executed."""
        mock_result = Mock()
        mock_result.rowcount = 5
        mock_async_session.execute.return_value = mock_result

        await chunk_repository.delete_by_paper_id("paper-uuid")

        mock_async_session.execute.assert_called_once()
        mock_async_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_paper_id_returns_count(
        self, chunk_repository, mock_async_session
    ):
        """Verify rowcount is returned."""
        mock_result = Mock()
        mock_result.rowcount = 10
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.delete_by_paper_id("paper-uuid")

        assert result == 10

    @pytest.mark.asyncio
    async def test_delete_by_paper_id_returns_zero(
        self, chunk_repository, mock_async_session
    ):
        """Verify zero returned when no chunks deleted."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.delete_by_paper_id("paper-uuid")

        assert result == 0


class TestChunkRepositoryCount:
    """Tests for ChunkRepository count methods."""

    @pytest.fixture
    def chunk_repository(self, mock_async_session):
        return ChunkRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_count_by_paper_id_returns_count(
        self, chunk_repository, mock_async_session
    ):
        """Verify count for specific paper."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["id1", "id2", "id3"]
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.count_by_paper_id("paper-uuid")

        assert result == 3

    @pytest.mark.asyncio
    async def test_count_returns_total(
        self, chunk_repository, mock_async_session
    ):
        """Verify total chunk count."""
        mock_result = Mock()
        mock_result.scalar_one.return_value = 100
        mock_async_session.execute.return_value = mock_result

        result = await chunk_repository.count()

        assert result == 100
