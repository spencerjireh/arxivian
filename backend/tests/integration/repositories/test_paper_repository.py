"""Integration tests for PaperRepository with real database."""

import pytest
import uuid
from datetime import datetime, timezone

from src.repositories.paper_repository import PaperRepository


class TestPaperRepositoryCRUD:
    """Test basic CRUD operations against real database."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_paper(self, db_session, sample_paper_data):
        """Verify paper can be created and retrieved."""
        repo = PaperRepository(session=db_session)

        paper = await repo.create(sample_paper_data)

        assert paper.id is not None
        assert paper.arxiv_id == sample_paper_data["arxiv_id"]
        assert paper.title == sample_paper_data["title"]
        assert paper.authors == sample_paper_data["authors"]

        retrieved = await repo.get_by_id(str(paper.id))
        assert retrieved is not None
        assert retrieved.arxiv_id == sample_paper_data["arxiv_id"]

    @pytest.mark.asyncio
    async def test_get_by_arxiv_id(self, db_session, sample_paper_data):
        """Verify paper can be retrieved by arXiv ID."""
        repo = PaperRepository(session=db_session)

        paper = await repo.create(sample_paper_data)

        retrieved = await repo.get_by_arxiv_id(sample_paper_data["arxiv_id"])
        assert retrieved is not None
        assert retrieved.id == paper.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        """Verify None returned for nonexistent paper."""
        repo = PaperRepository(session=db_session)

        retrieved = await repo.get_by_id(str(uuid.uuid4()))
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_paper(self, db_session, sample_paper_data):
        """Verify paper can be updated."""
        repo = PaperRepository(session=db_session)
        paper = await repo.create(sample_paper_data)

        updated = await repo.update(
            str(paper.id), {"title": "Updated Title", "abstract": "New abstract."}
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.abstract == "New abstract."
        assert updated.arxiv_id == sample_paper_data["arxiv_id"]

    @pytest.mark.asyncio
    async def test_delete_paper(self, db_session, sample_paper_data):
        """Verify paper can be deleted."""
        repo = PaperRepository(session=db_session)
        paper = await repo.create(sample_paper_data)
        paper_id = str(paper.id)

        deleted = await repo.delete(paper_id)
        assert deleted is True

        retrieved = await repo.get_by_id(paper_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_paper(self, db_session):
        """Verify deleting nonexistent paper returns False."""
        repo = PaperRepository(session=db_session)

        deleted = await repo.delete(str(uuid.uuid4()))
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, db_session, sample_paper_data):
        """Verify exists returns True for existing paper."""
        repo = PaperRepository(session=db_session)
        await repo.create(sample_paper_data)

        exists = await repo.exists(sample_paper_data["arxiv_id"])
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, db_session):
        """Verify exists returns False for nonexistent paper."""
        repo = PaperRepository(session=db_session)

        exists = await repo.exists("nonexistent-arxiv-id")
        assert exists is False

    @pytest.mark.asyncio
    async def test_count(self, db_session, sample_paper_data):
        """Verify count returns correct number."""
        repo = PaperRepository(session=db_session)

        initial_count = await repo.count()

        await repo.create(sample_paper_data)
        await repo.create({**sample_paper_data, "arxiv_id": "2301.99999"})

        final_count = await repo.count()
        assert final_count == initial_count + 2


class TestPaperRepositoryFiltering:
    """Test filtering and pagination."""

    @pytest.mark.asyncio
    async def test_get_all_pagination(self, db_session, sample_paper_data):
        """Verify pagination works correctly."""
        repo = PaperRepository(session=db_session)

        for i in range(5):
            data = {**sample_paper_data, "arxiv_id": f"2301.{i:05d}"}
            await repo.create(data)

        papers, total = await repo.get_all(offset=0, limit=2)
        assert total == 5
        assert len(papers) == 2

        papers, total = await repo.get_all(offset=2, limit=2)
        assert total == 5
        assert len(papers) == 2

        papers, total = await repo.get_all(offset=4, limit=2)
        assert total == 5
        assert len(papers) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_category_filter(self, db_session, sample_paper_data):
        """Verify category filtering works."""
        repo = PaperRepository(session=db_session)
        uid = sample_paper_data["user_id"]

        await repo.create(
            {
                "arxiv_id": "2301.00001",
                "user_id": uid,
                "title": "ML Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.LG"],
                "published_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
            }
        )
        await repo.create(
            {
                "arxiv_id": "2301.00002",
                "user_id": uid,
                "title": "AI Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "categories": ["cs.AI"],
                "published_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "pdf_url": "https://arxiv.org/pdf/2301.00002.pdf",
            }
        )

        papers, total = await repo.get_all(category_filter="cs.LG")
        assert total == 1
        assert papers[0].arxiv_id == "2301.00001"


class TestPaperRepositoryProcessing:
    """Test processing-related operations."""

    @pytest.mark.asyncio
    async def test_mark_as_processed(self, db_session, sample_paper_data):
        """Verify marking paper as processed updates all fields."""
        repo = PaperRepository(session=db_session)
        paper = await repo.create(sample_paper_data)

        assert paper.pdf_processed is False

        updated = await repo.mark_as_processed(
            paper_id=str(paper.id),
            raw_text="Full paper text content...",
            sections=[{"name": "Introduction", "text": "Intro text"}],
            parser_used="marker",
        )

        assert updated is not None
        assert updated.pdf_processed is True
        assert updated.raw_text == "Full paper text content..."
        assert updated.parser_used == "marker"
        assert updated.pdf_processing_date is not None

    @pytest.mark.asyncio
    async def test_get_unprocessed_papers(self, db_session, sample_paper_data):
        """Verify unprocessed papers filter."""
        repo = PaperRepository(session=db_session)

        unprocessed = await repo.create(sample_paper_data)

        processed_data = {
            **sample_paper_data,
            "arxiv_id": "2301.99999",
            "pdf_processed": True,
            "pdf_processing_date": datetime.now(timezone.utc),
            "parser_used": "marker",
            "raw_text": "Text",
        }
        await repo.create(processed_data)

        papers = await repo.get_unprocessed_papers()
        assert len(papers) == 1
        assert papers[0].id == unprocessed.id

    @pytest.mark.asyncio
    async def test_get_orphaned_papers(self, db_session, sample_paper_data):
        """Verify orphaned papers detection (papers with no chunks)."""
        repo = PaperRepository(session=db_session)

        # Create a processed paper with no chunks
        processed_data = {
            **sample_paper_data,
            "pdf_processed": True,
            "pdf_processing_date": datetime.now(timezone.utc),
            "parser_used": "marker",
            "raw_text": "Text",
        }
        paper = await repo.create(processed_data)

        orphaned = await repo.get_orphaned_papers()
        assert any(p.id == paper.id for p in orphaned)
