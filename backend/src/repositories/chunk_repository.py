"""Repository for Chunk model operations."""

from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chunk import Chunk
from src.utils.logger import get_logger

log = get_logger(__name__)


class ChunkRepository:
    """Repository for Chunk CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bulk(self, chunks_data: List[dict]) -> List[Chunk]:
        """Create multiple chunks at once."""
        chunks = [Chunk(**data) for data in chunks_data]
        self.session.add_all(chunks)
        await self.session.commit()
        for chunk in chunks:
            await self.session.refresh(chunk)
        log.debug("chunks created", count=len(chunks))
        return chunks

    async def get_by_paper_id(self, paper_id: str) -> List[Chunk]:
        """Get all chunks for a paper."""
        result = await self.session.execute(
            select(Chunk).where(Chunk.paper_id == paper_id).order_by(Chunk.chunk_index)
        )
        chunks = list(result.scalars().all())
        log.debug("chunks query by paper_id", paper_id=paper_id, count=len(chunks))
        return chunks

    async def get_by_arxiv_id(self, arxiv_id: str) -> List[Chunk]:
        """Get all chunks for a paper by arXiv ID."""
        result = await self.session.execute(
            select(Chunk).where(Chunk.arxiv_id == arxiv_id).order_by(Chunk.chunk_index)
        )
        chunks = list(result.scalars().all())
        log.debug("chunks query by arxiv_id", arxiv_id=arxiv_id, count=len(chunks))
        return chunks

    async def delete_by_paper_id(self, paper_id: str) -> int:
        """Delete all chunks for a paper. Returns count deleted."""
        result = await self.session.execute(delete(Chunk).where(Chunk.paper_id == paper_id))
        await self.session.commit()
        count = result.rowcount or 0
        log.debug("chunks deleted", paper_id=paper_id, count=count)
        return count

    async def count_by_paper_id(self, paper_id: str) -> int:
        """Count chunks for a paper."""
        result = await self.session.execute(select(Chunk.id).where(Chunk.paper_id == paper_id))
        return len(list(result.scalars().all()))

    async def count(self) -> int:
        """Get total count of chunks."""
        from sqlalchemy import func

        result = await self.session.execute(select(func.count()).select_from(Chunk))
        return result.scalar_one()
