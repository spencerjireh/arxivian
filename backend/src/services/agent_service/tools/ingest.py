"""Ingest papers tool for arXiv paper ingestion."""

from typing import List, Optional

from src.services.ingest_service import IngestService
from src.schemas.ingest import IngestRequest
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

log = get_logger(__name__)

AGENT_MAX_RESULTS = 10


class IngestPapersTool(BaseTool):
    """Tool for ingesting research papers from arXiv."""

    name = "ingest_papers"
    description = (
        "Ingest research papers from arXiv into the knowledge base. "
        "Use when the user asks to add, import, or download papers. "
        "Provide either a search query OR specific arXiv IDs (not both). "
        "Limited to 10 papers per call."
    )

    def __init__(self, ingest_service: IngestService):
        """
        Initialize ingest tool.

        Args:
            ingest_service: Service for paper ingestion pipeline
        """
        self.ingest_service = ingest_service

    @property
    def parameters_schema(self) -> dict:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "arXiv search query (mutually exclusive with arxiv_ids)",
                },
                "arxiv_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of arXiv IDs to ingest (mutually exclusive with query)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum papers to ingest (1-10)",
                    "default": 5,
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "arXiv categories filter (query mode only)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Filter by date (YYYY-MM-DD, query mode only)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Filter by date (YYYY-MM-DD, query mode only)",
                },
                "force_reprocess": {
                    "type": "boolean",
                    "description": "Re-process existing papers",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(
        self,
        query: Optional[str] = None,
        arxiv_ids: Optional[List[str]] = None,
        max_results: int = 5,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_reprocess: bool = False,
        **kwargs,
    ) -> ToolResult:
        """
        Execute paper ingestion.

        Args:
            query: arXiv search query (mode 1)
            arxiv_ids: List of arXiv IDs to ingest (mode 2)
            max_results: Maximum papers to ingest
            categories: arXiv categories filter (query mode only)
            start_date: Start date filter (query mode only)
            end_date: End date filter (query mode only)
            force_reprocess: Re-process existing papers

        Returns:
            ToolResult with ingestion summary
        """
        # Validate input
        if query and arxiv_ids:
            return ToolResult(
                success=False,
                error="Provide either 'query' or 'arxiv_ids', not both",
                tool_name=self.name,
            )

        if not query and not arxiv_ids:
            return ToolResult(
                success=False,
                error="Must provide either 'query' or 'arxiv_ids'",
                tool_name=self.name,
            )

        max_results = min(max_results, AGENT_MAX_RESULTS)

        log.debug(
            "ingest_papers executing",
            mode="query" if query else "ids",
            max_results=max_results,
        )

        try:
            if query:
                request = IngestRequest(
                    query=query,
                    max_results=max_results,
                    categories=categories,
                    start_date=start_date,
                    end_date=end_date,
                    force_reprocess=force_reprocess,
                )
                response = await self.ingest_service.ingest_papers(request)
            else:
                # arxiv_ids is guaranteed non-None here (validated above)
                ids = arxiv_ids[:max_results] if arxiv_ids else []
                response = await self.ingest_service.ingest_by_ids(ids, force_reprocess)

            summary = {
                "status": response.status,
                "papers_fetched": response.papers_fetched,
                "papers_processed": response.papers_processed,
                "chunks_created": response.chunks_created,
                "duration_seconds": round(response.duration_seconds, 2),
                "papers": [
                    {"arxiv_id": p.arxiv_id, "title": p.title[:80], "chunks": p.chunks_created}
                    for p in response.papers
                ],
                "errors": [
                    {"arxiv_id": e.arxiv_id, "error": e.error[:100]} for e in response.errors
                ],
            }

            log.debug("ingest_papers completed", papers=response.papers_processed)

            return ToolResult(
                success=response.status == "completed",
                data=summary,
                error=f"{len(response.errors)} papers failed" if response.errors else None,
                tool_name=self.name,
            )

        except Exception as e:
            log.error("ingest_papers failed", error=str(e))
            return ToolResult(success=False, error=str(e), tool_name=self.name)
