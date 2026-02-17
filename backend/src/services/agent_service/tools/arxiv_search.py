"""arXiv search tool for querying papers without ingesting."""

from typing import ClassVar

from src.clients.arxiv_client import ArxivClient
from src.utils.logger import get_logger

from .base import BaseTool, ToolResult
from .utils import format_paper_for_prompt, parse_date

log = get_logger(__name__)


def _format_search_results(data: dict) -> str:
    """Format arxiv search results into compact prompt text."""
    papers = data.get("papers", [])
    if not papers:
        return data.get("message", "") or "No papers found."
    lines = [f"Found {len(papers)} papers:"]
    for i, p in enumerate(papers, 1):
        lines.append(format_paper_for_prompt(p, i))
    return "\n".join(lines)


class ArxivSearchTool(BaseTool):
    """Tool for searching arXiv without ingesting papers."""

    name = "arxiv_search"
    description = (
        "Search arXiv for papers matching a query. Returns metadata only without "
        "downloading or processing. Use when user wants to find papers on arXiv "
        "or explore what's available before deciding to ingest."
    )

    extends_chunks: ClassVar[bool] = False
    required_dependencies: ClassVar[list[str]] = ["arxiv_client"]

    def __init__(self, arxiv_client: ArxivClient):
        self.arxiv_client = arxiv_client

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query for arXiv (e.g., 'transformer attention mechanism'). "
                        "Use plain keywords -- do NOT include raw arXiv API syntax like "
                        "'submittedDate:' here. Use start_date/end_date parameters for dates."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum papers to return (1-10, default 5)",
                    "default": 5,
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by arXiv categories (e.g., ['cs.LG', 'cs.AI'])",
                },
                "start_date": {
                    "type": "string",
                    "description": "Papers published after (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Papers published before (YYYY-MM-DD)",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        categories: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs,
    ) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(
                success=False,
                error="Query is required. Provide keywords (e.g. 'machine learning'). "
                "Use start_date/end_date parameters for date filtering.",
                tool_name=self.name,
            )

        max_results = min(max(1, max_results), 10)
        log.debug("arxiv_search", query=query, max_results=max_results, categories=categories)

        try:
            start_dt = parse_date(start_date, "start_date")
            end_dt = parse_date(end_date, "end_date")
        except ValueError as e:
            return ToolResult(success=False, error=str(e), tool_name=self.name)

        try:
            papers = await self.arxiv_client.search_papers(
                query=query,
                max_results=max_results,
                categories=categories,
                start_date=start_dt.isoformat() if start_dt else None,
                end_date=end_dt.isoformat() if end_dt else None,
            )

            results = [
                {
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "authors": p.authors,
                    "abstract": p.abstract[:500] + "..." if len(p.abstract) > 500 else p.abstract,
                    "categories": p.categories,
                    "published_date": p.published_date.isoformat() if p.published_date else None,
                    "pdf_url": p.pdf_url,
                }
                for p in papers
            ]

            log.debug("arxiv_search completed", count=len(results))
            data: dict = {"count": len(results), "papers": results}
            if not results and (start_date or end_date):
                data["message"] = (
                    "No papers matched the given date range. "
                    "Try broadening the date window or adjusting your query."
                )
            return ToolResult(
                success=True,
                data=data,
                prompt_text=_format_search_results(data),
                tool_name=self.name,
            )
        except Exception as e:
            log.error("arxiv_search failed", error=str(e), exc_info=True)
            return ToolResult(success=False, error=str(e), tool_name=self.name)
