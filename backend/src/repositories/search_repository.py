"""Repository for search operations with hybrid search support."""

from typing import List, Optional
from dataclasses import dataclass
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chunk import Chunk
from src.models.paper import Paper


@dataclass
class SearchResult:
    """Search result with chunk and paper metadata."""

    chunk_id: str
    paper_id: str
    arxiv_id: str
    title: str
    authors: List[str]
    chunk_text: str
    section_name: Optional[str]
    page_number: Optional[int]
    score: float
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    published_date: Optional[str] = None
    pdf_url: Optional[str] = None


class SearchRepository:
    """Repository for hybrid search operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def vector_search(
        self, query_embedding: List[float], top_k: int = 10, min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Vector similarity search using cosine distance.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of SearchResult objects ordered by similarity
        """
        # Convert embedding to string format for pgvector
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        query = text("""
            SELECT 
                c.id as chunk_id,
                c.paper_id,
                c.arxiv_id,
                p.title,
                p.authors,
                c.chunk_text,
                c.section_name,
                c.page_number,
                1 - (c.embedding <=> :embedding::vector) as score,
                p.published_date,
                p.pdf_url
            FROM chunks c
            JOIN papers p ON c.paper_id = p.id
            WHERE 1 - (c.embedding <=> :embedding::vector) >= :min_score
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self.session.execute(
            query, {"embedding": embedding_str, "min_score": min_score, "limit": top_k}
        )

        return [
            SearchResult(
                chunk_id=str(row.chunk_id),
                paper_id=str(row.paper_id),
                arxiv_id=row.arxiv_id,
                title=row.title,
                authors=row.authors,
                chunk_text=row.chunk_text,
                section_name=row.section_name,
                page_number=row.page_number,
                score=float(row.score),
                vector_score=float(row.score),
                published_date=str(row.published_date) if row.published_date else None,
                pdf_url=row.pdf_url,
            )
            for row in result.fetchall()
        ]

    async def fulltext_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Full-text search using PostgreSQL tsvector.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of SearchResult objects ordered by text rank
        """
        search_query = text("""
            SELECT 
                c.id as chunk_id,
                c.paper_id,
                c.arxiv_id,
                p.title,
                p.authors,
                c.chunk_text,
                c.section_name,
                c.page_number,
                ts_rank(c.search_vector, to_tsquery('english', :query)) as score,
                p.published_date,
                p.pdf_url
            FROM chunks c
            JOIN papers p ON c.paper_id = p.id
            WHERE c.search_vector @@ to_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :limit
        """)

        # Prepare query for tsquery (handle spaces and special chars)
        prepared_query = " & ".join(query.split())

        result = await self.session.execute(search_query, {"query": prepared_query, "limit": top_k})

        return [
            SearchResult(
                chunk_id=str(row.chunk_id),
                paper_id=str(row.paper_id),
                arxiv_id=row.arxiv_id,
                title=row.title,
                authors=row.authors,
                chunk_text=row.chunk_text,
                section_name=row.section_name,
                page_number=row.page_number,
                score=float(row.score),
                text_score=float(row.score),
                published_date=str(row.published_date) if row.published_date else None,
                pdf_url=row.pdf_url,
            )
            for row in result.fetchall()
        ]
