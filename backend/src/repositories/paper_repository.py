"""Repository for Paper model operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chunk import Chunk
from src.models.paper import Paper
from src.utils.logger import get_logger

log = get_logger(__name__)


class PaperRepository:
    """Repository for Paper CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, paper_id: str) -> Paper | None:
        """Get paper by UUID."""
        log.debug("query paper by id", paper_id=paper_id)
        result = await self.session.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        log.debug("query result", found=paper is not None)
        return paper

    async def get_by_ids(self, paper_ids: list[uuid.UUID]) -> list[Paper]:
        """Batch fetch by UUID (feed enrichment). Empty input -> empty list, no query."""
        if not paper_ids:
            return []
        result = await self.session.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        return list(result.scalars().all())

    async def get_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
        """Get paper by arXiv ID."""
        log.debug("query paper by arxiv_id", arxiv_id=arxiv_id)
        stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
        result = await self.session.execute(stmt)
        paper = result.scalar_one_or_none()
        log.debug("query result", found=paper is not None)
        return paper

    async def get_by_arxiv_id_for_update(self, arxiv_id: str) -> Paper | None:
        """
        Get paper by arXiv ID with row-level lock.

        Use this when you need to check-then-update to prevent race conditions.
        The lock is released when the transaction commits or rolls back.

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Paper if found, None otherwise

        Raises:
            OperationalError: If the row is already locked by another transaction
        """
        log.debug("query paper by arxiv_id with lock", arxiv_id=arxiv_id)
        stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
        result = await self.session.execute(stmt.with_for_update(nowait=True))
        paper = result.scalar_one_or_none()
        log.debug("query result with lock", found=paper is not None)
        return paper

    async def create(self, paper_data: dict) -> Paper:
        """Create a new paper. Caller is responsible for committing the transaction."""
        paper = Paper(**paper_data)
        self.session.add(paper)
        await self.session.flush()
        await self.session.refresh(paper)
        log.debug("paper created", arxiv_id=paper.arxiv_id)
        return paper

    async def update(self, paper_id: str, update_data: dict) -> Paper | None:
        """Update paper. Caller is responsible for committing the transaction."""
        update_data["updated_at"] = datetime.now(UTC)
        await self.session.execute(update(Paper).where(Paper.id == paper_id).values(**update_data))
        await self.session.flush()
        log.debug("paper updated", paper_id=paper_id)
        # Expire cached object so get_by_id returns fresh data from DB
        self.session.expire_all()
        return await self.get_by_id(paper_id)

    async def exists(self, arxiv_id: str) -> bool:
        """Check if paper exists by arXiv ID."""
        result = await self.session.execute(select(Paper.id).where(Paper.arxiv_id == arxiv_id))
        return result.scalar_one_or_none() is not None

    async def get_existing_arxiv_ids(self, arxiv_ids: list[str]) -> set[str]:
        """Return the subset of arxiv_ids that already exist in the database."""
        if not arxiv_ids:
            return set()
        result = await self.session.execute(
            select(Paper.arxiv_id).where(Paper.arxiv_id.in_(arxiv_ids))
        )
        return set(result.scalars().all())

    async def count(self) -> int:
        """Get total count of papers."""
        result = await self.session.execute(select(func.count()).select_from(Paper))
        return result.scalar_one()

    async def delete(self, paper_id: str) -> bool:
        """
        Delete a paper by ID. Caller is responsible for committing the transaction.

        Chunks are automatically deleted via CASCADE foreign key.

        Args:
            paper_id: UUID of the paper to delete

        Returns:
            True if paper was deleted, False if not found
        """
        result = await self.session.execute(delete(Paper).where(Paper.id == paper_id))
        await self.session.flush()
        deleted = (result.rowcount or 0) > 0  # ty: ignore[unresolved-attribute]
        if deleted:
            log.info("paper deleted", paper_id=paper_id)
        return deleted

    async def delete_by_arxiv_id(self, arxiv_id: str) -> bool:
        """
        Delete a paper by arXiv ID. Caller is responsible for committing the transaction.

        Chunks are automatically deleted via CASCADE foreign key.

        Args:
            arxiv_id: arXiv ID of the paper to delete

        Returns:
            True if paper was deleted, False if not found
        """
        stmt = delete(Paper).where(Paper.arxiv_id == arxiv_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        deleted = (result.rowcount or 0) > 0  # ty: ignore[unresolved-attribute]
        if deleted:
            log.info("paper deleted", arxiv_id=arxiv_id)
        return deleted

    async def get_orphaned_papers(self) -> list[Paper]:
        """
        Find papers that are marked as processed but have no chunks.

        These represent failed ingestions where the paper was created
        but chunk creation failed.

        Returns:
            List of orphaned Paper objects
        """
        # Use NOT EXISTS for better performance on large datasets
        has_chunk = select(1).where(Chunk.paper_id == Paper.id).exists()

        # Find processed papers that have no chunks
        stmt = (
            select(Paper)
            .where(Paper.pdf_processed == True)  # noqa: E712
            .where(~has_chunk)
        )

        result = await self.session.execute(stmt)
        papers = list(result.scalars().all())
        log.debug("orphaned papers query", count=len(papers))
        return papers
