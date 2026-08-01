"""Semantic Scholar tool -- citation metrics (how cited / how fast) for a paper."""

from typing import ClassVar

from src.clients.semantic_scholar_client import CitationMetrics, SemanticScholarClient
from src.utils.logger import get_logger

from .base import BaseTool, ToolResult

log = get_logger(__name__)


def _format_metrics(metrics: CitationMetrics) -> str:
    """Format citation metrics into compact prompt text."""
    if not metrics.found:
        return f"No Semantic Scholar record found for arXiv:{metrics.arxiv_id}."
    return (
        f"arXiv:{metrics.arxiv_id} -- {metrics.citation_count} citations "
        f"({metrics.influential_citation_count} influential), "
        f"{metrics.citations_per_month} citations/month "
        f"(demand: {metrics.demand_band})."
    )


class SemanticScholarTool(BaseTool):
    """Tool for looking up a paper's citation count and velocity via Semantic Scholar."""

    name = "semantic_scholar"
    description = (
        "Look up how widely cited a paper is via Semantic Scholar. Returns total and "
        "influential citation counts plus citation velocity (citations per month), which "
        "signals demand/uptake. Use when asked how popular, cited, or impactful a specific "
        "paper is. Requires the paper's arXiv ID."
    )

    extends_chunks: ClassVar[bool] = False
    required_dependencies: ClassVar[list[str]] = ["semantic_scholar_client"]

    def __init__(self, semantic_scholar_client: SemanticScholarClient):
        self.semantic_scholar_client = semantic_scholar_client

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv ID of the paper (e.g., '2301.00001')",
                },
            },
            "required": ["arxiv_id"],
        }

    async def execute(self, arxiv_id: str, **kwargs) -> ToolResult:  # type: ignore[override]
        if not arxiv_id or not arxiv_id.strip():
            return ToolResult(
                success=False,
                error="arxiv_id is required (e.g. '2301.00001').",
                tool_name=self.name,
            )

        log.debug("semantic_scholar", arxiv_id=arxiv_id)

        try:
            metrics = await self.semantic_scholar_client.get_citation_metrics(arxiv_id.strip())
            return ToolResult(
                success=True,
                data=metrics.model_dump(),
                prompt_text=_format_metrics(metrics),
                tool_name=self.name,
            )
        except Exception as e:
            log.error("semantic_scholar failed", error=str(e), exc_info=True)
            return ToolResult(success=False, error=str(e), tool_name=self.name)
