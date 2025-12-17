"""Retrieve chunks tool for vector search."""

from src.services.search_service import SearchService
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

log = get_logger(__name__)


class RetrieveChunksTool(BaseTool):
    """
    Tool for retrieving relevant document chunks from the vector database.

    Uses hybrid search (semantic + keyword) to find the most relevant chunks
    for a given query.
    """

    name = "retrieve_chunks"
    description = (
        "Search the AI/ML research paper database for relevant document chunks. "
        "Use this when you need information from academic papers about machine learning, "
        "deep learning, transformers, neural networks, or related AI topics."
    )

    def __init__(self, search_service: SearchService, default_top_k: int = 6):
        """
        Initialize retrieve tool.

        Args:
            search_service: Service for vector/hybrid search
            default_top_k: Default number of chunks to retrieve
        """
        self.search_service = search_service
        self.default_top_k = default_top_k

    @property
    def parameters_schema(self) -> dict:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding relevant research paper chunks",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of chunks to retrieve",
                    "default": self.default_top_k,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, top_k: int | None = None, **kwargs) -> ToolResult:
        """
        Execute chunk retrieval.

        Args:
            query: Search query
            top_k: Number of chunks to retrieve (uses default if not provided)

        Returns:
            ToolResult with list of chunk dictionaries
        """
        top_k = top_k or self.default_top_k

        log.debug("retrieve_chunks executing", query=query[:100], top_k=top_k)

        try:
            results = await self.search_service.hybrid_search(
                query=query,
                top_k=top_k,
                mode="hybrid",
            )

            chunks = [
                {
                    "chunk_id": str(r.chunk_id),
                    "chunk_text": r.chunk_text,
                    "arxiv_id": r.arxiv_id,
                    "title": r.title,
                    "authors": r.authors if hasattr(r, "authors") else [],
                    "section_name": r.section_name,
                    "score": r.score,
                    "pdf_url": (
                        r.pdf_url
                        if hasattr(r, "pdf_url")
                        else f"https://arxiv.org/pdf/{r.arxiv_id}.pdf"
                    ),
                    "published_date": r.published_date if hasattr(r, "published_date") else None,
                }
                for r in results
            ]

            log.debug("retrieve_chunks completed", chunks_found=len(chunks))

            return ToolResult(
                success=True,
                data=chunks,
                tool_name=self.name,
            )

        except Exception as e:
            log.error("retrieve_chunks failed", error=str(e))
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
            )
