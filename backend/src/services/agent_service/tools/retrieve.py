"""Retrieve chunks tool for vector search."""

from typing import ClassVar

from src.services.search_service import SearchService
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

log = get_logger(__name__)

MAX_TOP_K = 50


class RetrieveChunksTool(BaseTool):
    """Tool for retrieving relevant document chunks from the vector database."""

    name = "retrieve_chunks"
    description = (
        "Answer questions using papers already in the knowledge base. "
        "Retrieves relevant passages from ingested arXiv papers. "
        "This is the DEFAULT tool for any content question about research topics."
    )

    extends_chunks: ClassVar[bool] = True
    required_dependencies: ClassVar[list[str]] = ["search_service"]

    def __init__(
        self,
        search_service: SearchService,
        default_top_k: int = 6,
        min_score: float = 0.5,
    ):
        """
        Initialize retrieve tool.

        Args:
            search_service: Service for vector/hybrid search
            default_top_k: Default number of chunks to retrieve
            min_score: Minimum RRF score to include a chunk (0.0-1.0)
        """
        self.search_service = search_service
        self.default_top_k = default_top_k
        self.min_score = min_score

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding relevant research paper chunks",
                },
                "top_k": {
                    "type": "integer",
                    "description": f"Number of chunks to retrieve (1-{MAX_TOP_K})",
                    "default": self.default_top_k,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, top_k: int | None = None, **kwargs) -> ToolResult:  # type: ignore[override]
        if not query or not query.strip():
            return ToolResult(success=False, error="Query cannot be empty", tool_name=self.name)

        effective_top_k = top_k if top_k is not None else self.default_top_k
        clamped_top_k = max(1, min(effective_top_k, MAX_TOP_K))
        log.debug("retrieve_chunks executing", query=query[:100], top_k=clamped_top_k)

        try:
            results = await self.search_service.hybrid_search(
                query=query,
                top_k=clamped_top_k,
                mode="hybrid",
            )

            results = [r for r in results if r.score >= self.min_score]

            chunks = [
                {
                    "chunk_id": str(r.chunk_id),
                    "chunk_text": r.chunk_text,
                    "arxiv_id": r.arxiv_id,
                    "title": r.title,
                    "authors": r.authors,
                    "section_name": r.section_name,
                    "score": r.score,
                    "pdf_url": getattr(r, "pdf_url", None)
                    or f"https://arxiv.org/pdf/{r.arxiv_id}.pdf",
                    "published_date": getattr(r, "published_date", None),
                }
                for r in results
            ]

            log.debug("retrieve_chunks completed", chunks_found=len(chunks))
            return ToolResult(success=True, data=chunks, tool_name=self.name)

        except Exception as e:
            log.error("retrieve_chunks failed", error=str(e), exc_info=True)
            return ToolResult(success=False, error=str(e), tool_name=self.name)
