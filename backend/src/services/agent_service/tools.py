"""LangGraph tools for agent workflow."""

from typing import List
from langchain_core.tools import tool
from src.services.search_service import SearchService


def create_retrieve_tool(search_service: SearchService):
    """Create retrieval tool with search service injected."""

    @tool
    async def retrieve_chunks(query: str, top_k: int) -> List[dict]:
        """
        Retrieve relevant chunks from database using hybrid search.

        Args:
            query: Search query
            top_k: Number of chunks to retrieve

        Returns:
            List of chunk dictionaries with metadata
        """
        results = await search_service.hybrid_search(query=query, top_k=top_k, mode="hybrid")

        return [
            {
                "chunk_id": str(r.chunk_id),
                "chunk_text": r.chunk_text,
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "authors": r.authors if hasattr(r, "authors") else [],
                "section_name": r.section_name,
                "score": r.score,
                "pdf_url": r.pdf_url
                if hasattr(r, "pdf_url")
                else f"https://arxiv.org/pdf/{r.arxiv_id}.pdf",
                "published_date": r.published_date if hasattr(r, "published_date") else None,
            }
            for r in results
        ]

    return retrieve_chunks
