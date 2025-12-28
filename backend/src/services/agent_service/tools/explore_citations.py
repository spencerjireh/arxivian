"""Explore citations tool for retrieving paper references."""

from src.repositories.paper_repository import PaperRepository
from src.utils.logger import get_logger

from .base import BaseTool, ToolResult
from .utils import safe_list_from_jsonb

log = get_logger(__name__)


class ExploreCitationsTool(BaseTool):
    """Tool for exploring citations/references from ingested papers."""

    name = "explore_citations"
    description = (
        "Get the list of references cited by a paper in the knowledge base. "
        "Use when user wants to explore related work or find papers cited by a specific paper. "
        "Only works for papers that have been ingested and processed."
    )

    def __init__(self, paper_repository: PaperRepository):
        self.paper_repository = paper_repository

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

    async def execute(self, arxiv_id: str, **kwargs) -> ToolResult:
        log.debug("explore_citations", arxiv_id=arxiv_id)

        try:
            paper = await self.paper_repository.get_by_arxiv_id(arxiv_id)

            if not paper:
                return ToolResult(
                    success=False,
                    error=f"Paper {arxiv_id} not found in knowledge base",
                    tool_name=self.name,
                )

            if paper.pdf_processed is not True:
                return ToolResult(
                    success=False,
                    error=f"Paper {arxiv_id} has not been processed yet",
                    tool_name=self.name,
                )

            references = safe_list_from_jsonb(paper.references)

            log.debug("explore_citations completed", arxiv_id=arxiv_id, count=len(references))
            return ToolResult(
                success=True,
                data={
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "reference_count": len(references),
                    "references": references,
                },
                tool_name=self.name,
            )
        except Exception as e:
            log.error("explore_citations failed", error=str(e))
            return ToolResult(success=False, error=str(e), tool_name=self.name)
