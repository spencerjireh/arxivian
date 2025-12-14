"""Repository for Paper model operations."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.paper import Paper


class PaperRepository:
    """Repository for Paper CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get paper by UUID."""
        result = await self.session.execute(select(Paper).where(Paper.id == paper_id))
        return result.scalar_one_or_none()

    async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Get paper by arXiv ID."""
        result = await self.session.execute(select(Paper).where(Paper.arxiv_id == arxiv_id))
        return result.scalar_one_or_none()

    async def create(self, paper_data: dict) -> Paper:
        """Create a new paper."""
        paper = Paper(**paper_data)
        self.session.add(paper)
        await self.session.commit()
        await self.session.refresh(paper)
        return paper

    async def update(self, paper_id: str, update_data: dict) -> Optional[Paper]:
        """Update paper."""
        update_data["updated_at"] = datetime.utcnow()
        await self.session.execute(update(Paper).where(Paper.id == paper_id).values(**update_data))
        await self.session.commit()
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
            select(Paper).where(Paper.pdf_processed == False).limit(limit)
        )
        return list(result.scalars().all())

    async def exists(self, arxiv_id: str) -> bool:
        """Check if paper exists by arXiv ID."""
        result = await self.session.execute(select(Paper.id).where(Paper.arxiv_id == arxiv_id))
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Get total count of papers."""
        from sqlalchemy import func

        result = await self.session.execute(select(func.count()).select_from(Paper))
        return result.scalar_one()
