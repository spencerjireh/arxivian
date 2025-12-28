"""Summarize paper tool for generating paper summaries."""

from src.clients.base_llm_client import BaseLLMClient
from src.repositories.paper_repository import PaperRepository
from src.utils.logger import get_logger

from .base import BaseTool, ToolResult

log = get_logger(__name__)

SUMMARY_PROMPT = """Summarize this research paper abstract in 2-3 sentences. Focus on:
- The main problem or question addressed
- The key approach or method
- The primary findings or contributions

Title: {title}
Abstract: {abstract}

Provide only the summary, no preamble."""


class SummarizePaperTool(BaseTool):
    """Tool for generating paper summaries using LLM."""

    name = "summarize_paper"
    description = (
        "Generate a concise 2-3 sentence summary of a paper's abstract. "
        "Use when user wants a quick overview of what a paper is about. "
        "Only works for papers in the knowledge base."
    )

    def __init__(self, paper_repository: PaperRepository, llm_client: BaseLLMClient):
        self.paper_repository = paper_repository
        self.llm_client = llm_client

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "arXiv ID of the paper to summarize (e.g., '2301.00001')",
                },
            },
            "required": ["arxiv_id"],
        }

    async def execute(self, arxiv_id: str, **kwargs) -> ToolResult:
        log.debug("summarize_paper", arxiv_id=arxiv_id)

        try:
            paper = await self.paper_repository.get_by_arxiv_id(arxiv_id)

            if not paper:
                return ToolResult(
                    success=False,
                    error=f"Paper {arxiv_id} not found in knowledge base",
                    tool_name=self.name,
                )

            prompt = SUMMARY_PROMPT.format(title=paper.title, abstract=paper.abstract)

            summary = await self.llm_client.generate_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )

            log.debug("summarize_paper completed", arxiv_id=arxiv_id)
            return ToolResult(
                success=True,
                data={
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "summary": summary,
                },
                tool_name=self.name,
            )
        except Exception as e:
            log.error("summarize_paper failed", error=str(e))
            return ToolResult(success=False, error=str(e), tool_name=self.name)
