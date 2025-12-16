"""Repository for Paper model operations."""

from typing import Optional, List, Literal
from datetime import datetime
from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.paper import Paper
from src.utils.logger import get_logger

log = get_logger(__name__)


class PaperRepository:
    """Repository for Paper CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get paper by UUID."""
        log.debug("query paper by id", paper_id=paper_id)
        result = await self.session.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        log.debug("query result", found=paper is not None)
        return paper

    async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get paper by arXiv ID."""
        log.debug("query paper by arxiv_id", arxiv_id=arxiv_id)
        result = await self.session.execute(select(Paper).where(Paper.arxiv_id == arxiv_id))
        paper = result.scalar_one_or_none()
        log.debug("query result", found=paper is not None)
        return paper

    async def create(self, paper_data: dict) -> Paper:
        """Create a new paper."""
        paper = Paper(**paper_data)
        self.session.add(paper)
        await self.session.commit()
        await self.session.refresh(paper)
        log.debug("paper created", arxiv_id=paper.arxiv_id)
        return paper

    async def update(self, paper_id: str, update_data: dict) -> Optional[Paper]:
        """Update paper."""
        update_data["updated_at"] = datetime.utcnow()
        await self.session.execute(update(Paper).where(Paper.id == paper_id).values(**update_data))
        await self.session.commit()
        log.debug("paper updated", paper_id=paper_id)
        return await self.get_by_id(paper_id)

    async def mark_as_processed(
        self, paper_id: str, raw_text: str, sections: List[dict], parser_used: str
    ) -> Paper:
        """Mark paper as processed with content."""
        return await self.update(
            paper_id,
            {
                "raw_text": raw_text,
                "sections": sections,
                "pdf_processed": True,
                "pdf_processing_date": datetime.utcnow(),
                "parser_used": parser_used,
            },
        )

    async def get_unprocessed_papers(self, limit: int = 100) -> List[Paper]:
        """Get papers that haven't been processed yet."""
        result = await self.session.execute(
            select(Paper).where(Paper.pdf_processed.is_(False)).limit(limit)
        )
        papers = list(result.scalars().all())
        log.debug("unprocessed papers query", count=len(papers))
        return papers

    async def exists(self, arxiv_id: str) -> bool:
        """Check if paper exists by arXiv ID."""
        result = await self.session.execute(select(Paper.id).where(Paper.arxiv_id == arxiv_id))
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Get total count of papers."""
        result = await self.session.execute(select(func.count()).select_from(Paper))
        return result.scalar_one()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        processed_only: Optional[bool] = None,
        category_filter: Optional[str] = None,
        author_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: Literal["created_at", "published_date", "updated_at"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[List[Paper], int]:
        """
        Get paginated list of papers with optional filters.

        Args:
            offset: Number of papers to skip
            limit: Maximum number of papers to return
            processed_only: Filter by pdf_processed status
            category_filter: Filter by category (case-insensitive substring match)
            author_filter: Filter by author (case-insensitive substring match)
            start_date: Filter papers published on or after this date
            end_date: Filter papers published on or before this date
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of papers, total count matching filters)
        """
        log.debug(
            "papers query",
            offset=offset,
            limit=limit,
            processed_only=processed_only,
            category_filter=category_filter,
            sort_by=sort_by,
        )

        query = select(Paper)
        count_query = select(func.count()).select_from(Paper)

        def apply_filter(condition):
            nonlocal query, count_query
            query = query.where(condition)
            count_query = count_query.where(condition)

        if processed_only is not None:
            apply_filter(Paper.pdf_processed == processed_only)

        if category_filter:
            condition = func.exists(
                select(1).where(
                    func.lower(func.jsonb_array_elements_text(Paper.categories)).like(
                        f"%{category_filter.lower()}%"
                    )
                )
            )
            apply_filter(condition)

        if author_filter:
            condition = func.exists(
                select(1).where(
                    func.lower(func.jsonb_array_elements_text(Paper.authors)).like(
                        f"%{author_filter.lower()}%"
                    )
                )
            )
            apply_filter(condition)

        if start_date:
            apply_filter(Paper.published_date >= start_date)

        if end_date:
            apply_filter(Paper.published_date <= end_date)

        total = await self.session.scalar(count_query) or 0

        sort_column = getattr(Paper, sort_by)
        order_func = desc if sort_order == "desc" else asc
        query = query.order_by(order_func(sort_column)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        papers = list(result.scalars().all())

        log.debug("papers query result", count=len(papers), total=total)
        return papers, total

    async def delete(self, paper_id: str) -> bool:
        """
        Delete a paper by ID.

        Chunks are automatically deleted via CASCADE foreign key.

        Args:
            paper_id: UUID of the paper to delete

        Returns:
            True if paper was deleted, False if not found
        """
        result = await self.session.execute(delete(Paper).where(Paper.id == paper_id))
        deleted = (result.rowcount or 0) > 0
        if deleted:
            log.info("paper deleted", paper_id=paper_id)
        return deleted

    async def delete_by_arxiv_id(self, arxiv_id: str) -> bool:
        """
        Delete a paper by arXiv ID.

        Chunks are automatically deleted via CASCADE foreign key.

        Args:
            arxiv_id: arXiv ID of the paper to delete

        Returns:
            True if paper was deleted, False if not found
        """
        result = await self.session.execute(delete(Paper).where(Paper.arxiv_id == arxiv_id))
        deleted = (result.rowcount or 0) > 0
        if deleted:
            log.info("paper deleted", arxiv_id=arxiv_id)
        return deleted
