"""List papers tool for querying paper database."""

from datetime import datetime

from src.services.ingest_service import IngestService
from src.utils.logger import get_logger

from .base import BaseTool, ToolResult

log = get_logger(__name__)


def _parse_date(value: str | None, field: str) -> datetime | None:
    """Parse ISO date string, raising ValueError with descriptive message."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid {field}: '{value}'. Expected format: YYYY-MM-DD")


class ListPapersTool(BaseTool):
    """Tool for listing papers in the knowledge base."""

    name = "list_papers"
    description = (
        "List research papers stored in the knowledge base. "
        "Use when user asks what papers are available or wants to browse by topic/author/date. "
        "Returns metadata only - use retrieve_chunks for content search."
    )

    def __init__(self, ingest_service: IngestService):
        self.ingest_service = ingest_service

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for title/abstract",
                },
                "author": {
                    "type": "string",
                    "description": "Filter by author name",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by arXiv category (e.g., cs.LG)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Papers published after (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Papers published before (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max papers to return (default 20, max 50)",
                    "default": 20,
                },
            },
            "required": [],
        }

    async def execute(
        self,
        query: str | None = None,
        author: str | None = None,
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 20,
        **kwargs,
    ) -> ToolResult:
        limit = min(limit, 50)
        log.debug("list_papers", query=query, author=author, category=category, limit=limit)

        try:
            start_dt = _parse_date(start_date, "start_date")
            end_dt = _parse_date(end_date, "end_date")
        except ValueError as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

        try:
            papers, total = await self.ingest_service.list_papers(
                query=query,
                author=author,
                categories=[category] if category else None,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit,
            )

            log.debug("list_papers completed", total=total, returned=len(papers))
            return ToolResult(
                success=True,
                data={"total_count": total, "returned": len(papers), "papers": papers},
                tool_name=self.name,
            )
        except Exception as e:
            log.error("list_papers failed", error=str(e))
            return ToolResult(success=False, error=str(e), tool_name=self.name)
