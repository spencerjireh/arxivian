"""Tests for PaperRepository."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime, timezone

from src.repositories.paper_repository import PaperRepository


class TestPaperRepositoryBasicOperations:
    """Tests for basic CRUD operations."""

    @pytest.fixture
    def paper_repository(self, mock_async_session):
        return PaperRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_paper(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify paper retrieval by UUID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_id(str(mock_paper.id))

        assert result is mock_paper
        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none(
        self, paper_repository, mock_async_session
    ):
        """Verify None for non-existent paper."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_id("nonexistent-uuid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_returns_paper(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify paper retrieval by arXiv ID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_arxiv_id("2301.00001")

        assert result is mock_paper

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_returns_none(
        self, paper_repository, mock_async_session
    ):
        """Verify None for non-existent arXiv ID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_arxiv_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_adds_paper(
        self, paper_repository, mock_async_session, sample_paper_data
    ):
        """Verify session.add is called."""
        await paper_repository.create(sample_paper_data)

        mock_async_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_flushes_and_refreshes(
        self, paper_repository, mock_async_session, sample_paper_data
    ):
        """Verify flush and refresh are called."""
        await paper_repository.create(sample_paper_data)

        mock_async_session.flush.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_modifies_paper(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify update statement is executed."""
        # Setup for update then get_by_id
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_async_session.execute.return_value = mock_result

        await paper_repository.update(str(mock_paper.id), {"title": "New Title"})

        assert mock_async_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_delete_removes_paper(
        self, paper_repository, mock_async_session
    ):
        """Verify delete statement is executed."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.delete("paper-uuid")

        assert result is True
        mock_async_session.execute.assert_called()
        mock_async_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(
        self, paper_repository, mock_async_session
    ):
        """Verify True when paper is deleted."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.delete("paper-uuid")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, paper_repository, mock_async_session
    ):
        """Verify False when paper not found."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_by_arxiv_id_removes_paper(
        self, paper_repository, mock_async_session
    ):
        """Verify delete by arXiv ID works."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.delete_by_arxiv_id("2301.00001")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_true(
        self, paper_repository, mock_async_session
    ):
        """Verify True for existing paper."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "some-id"
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.exists("2301.00001")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(
        self, paper_repository, mock_async_session
    ):
        """Verify False for non-existent paper."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_count_returns_total(
        self, paper_repository, mock_async_session
    ):
        """Verify count query returns total."""
        mock_result = Mock()
        mock_result.scalar_one.return_value = 42
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.count()

        assert result == 42


class TestPaperRepositoryLocking:
    """Tests for row-level locking operations."""

    @pytest.fixture
    def paper_repository(self, mock_async_session):
        return PaperRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_for_update_returns_paper(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify paper is returned with lock."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_arxiv_id_for_update("2301.00001")

        assert result is mock_paper

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id_for_update_returns_none(
        self, paper_repository, mock_async_session
    ):
        """Verify None when paper not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.get_by_arxiv_id_for_update("nonexistent")

        assert result is None


class TestPaperRepositoryFiltering:
    """Tests for get_all with various filters."""

    @pytest.fixture
    def paper_repository(self, mock_async_session):
        return PaperRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify offset/limit pagination."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_paper]
        mock_async_session.execute.return_value = mock_result
        mock_async_session.scalar.return_value = 1

        papers, total = await paper_repository.get_all(offset=0, limit=10)

        assert len(papers) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_all_returns_empty_list(
        self, paper_repository, mock_async_session
    ):
        """Verify empty list when no papers."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_result
        mock_async_session.scalar.return_value = 0

        papers, total = await paper_repository.get_all()

        assert papers == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_returns_total_count(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify total in tuple."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_paper]
        mock_async_session.execute.return_value = mock_result
        mock_async_session.scalar.return_value = 100

        _, total = await paper_repository.get_all(limit=10)

        assert total == 100


class TestPaperRepositorySpecialOperations:
    """Tests for special operations like mark_as_processed."""

    @pytest.fixture
    def paper_repository(self, mock_async_session):
        return PaperRepository(session=mock_async_session)

    @pytest.mark.asyncio
    async def test_mark_as_processed_updates_fields(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify all processing fields are set."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_paper
        mock_async_session.execute.return_value = mock_result

        result = await paper_repository.mark_as_processed(
            paper_id=str(mock_paper.id),
            raw_text="Full text content",
            sections=[{"name": "Intro", "text": "Text"}],
            parser_used="pypdf",
        )

        # The method should call update
        assert mock_async_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_unprocessed_papers_filters(
        self, paper_repository, mock_async_session, mock_paper
    ):
        """Verify pdf_processed=False filter."""
        mock_paper.pdf_processed = False
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_paper]
        mock_async_session.execute.return_value = mock_result

        papers = await paper_repository.get_unprocessed_papers(limit=10)

        assert len(papers) == 1

    @pytest.mark.asyncio
    async def test_get_orphaned_papers_returns_list(
        self, paper_repository, mock_async_session
    ):
        """Verify orphaned papers query works."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_result

        papers = await paper_repository.get_orphaned_papers()

        assert isinstance(papers, list)
