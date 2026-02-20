"""Propose ingest tool for HITL paper ingestion."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from src.repositories.paper_repository import PaperRepository
from src.schemas.stream import IngestProposalPaper
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

if TYPE_CHECKING:
    from src.repositories.usage_counter_repository import UsageCounterRepository

log = get_logger(__name__)

MAX_PROPOSAL = 5


def _format_proposal_summary(papers: list[IngestProposalPaper]) -> str:
    """Format proposed papers into compact prompt text."""
    lines = [f"Proposed {len(papers)} papers for user confirmation:"]
    for i, p in enumerate(papers, 1):
        lines.append(f'{i}. "{p.title}" [{p.arxiv_id}]')
    return "\n".join(lines)


class ProposeIngestTool(BaseTool):
    """Propose papers for user confirmation before ingestion."""

    name = "propose_ingest"
    description = (
        "Propose papers for ingestion into the knowledge base. "
        "Use ONLY AFTER arxiv_search AND only when the user explicitly asked to "
        "find, add, import, or ingest new papers. "
        "Never propose ingestion on your own initiative. "
        "Provide the arXiv IDs from a previous arxiv_search result. "
        "Limited to 5 papers per proposal."
    )

    extends_chunks: ClassVar[bool] = False
    sets_pause: ClassVar[bool] = True
    required_dependencies: ClassVar[list[str]] = ["paper_repository"]

    def __init__(
        self,
        paper_repository: PaperRepository,
        daily_ingests: int | None = None,
        usage_counter_repo: UsageCounterRepository | None = None,
        user_id: UUID | None = None,
    ):
        self.paper_repository = paper_repository
        self.daily_ingests = daily_ingests
        self.usage_counter_repo = usage_counter_repo
        self.user_id = user_id

    @property
    def _quota_enabled(self) -> bool:
        return (
            self.daily_ingests is not None
            and self.usage_counter_repo is not None
            and self.user_id is not None
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "arxiv_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "arXiv IDs to propose for ingestion (from arxiv_search results)",
                },
            },
            "required": ["arxiv_ids"],
        }

    async def execute(  # type: ignore[override]
        self,
        arxiv_ids: list[str] | None = None,
        tool_outputs: list[dict] | None = None,
        **kwargs,
    ) -> ToolResult:
        if not arxiv_ids:
            return ToolResult(
                success=False,
                error="Must provide arxiv_ids to propose for ingestion",
                tool_name=self.name,
            )

        # Validate prior arxiv_search in tool_outputs
        tool_outputs = tool_outputs or []
        prior_search = None
        for to in tool_outputs:
            if to.get("tool_name") == "arxiv_search":
                prior_search = to
                break

        if prior_search is None:
            return ToolResult(
                success=False,
                error=(
                    "propose_ingest requires a prior arxiv_search in the same turn. "
                    "Run arxiv_search first to find papers, then propose them."
                ),
                tool_name=self.name,
            )

        # Cap at MAX_PROPOSAL
        arxiv_ids = arxiv_ids[:MAX_PROPOSAL]

        # Enforce daily ingest quota
        if self._quota_enabled:
            assert self.usage_counter_repo is not None
            assert self.user_id is not None
            assert self.daily_ingests is not None
            count = await self.usage_counter_repo.get_today_ingest_count(self.user_id)
            if count >= self.daily_ingests:
                return ToolResult(
                    success=False,
                    prompt_text=(
                        f"Daily ingest limit reached ({count}/{self.daily_ingests}). "
                        "The user's free-tier quota resets at midnight UTC. "
                        "Suggest upgrading to Pro for unlimited ingestion."
                    ),
                    tool_name=self.name,
                )

        # Filter out already-ingested papers (single query)
        existing = await self.paper_repository.get_existing_arxiv_ids(arxiv_ids)
        remaining_ids = [aid for aid in arxiv_ids if aid not in existing]

        if not remaining_ids:
            return ToolResult(
                success=True,
                data={"papers": [], "proposed_ids": []},
                prompt_text="All proposed papers are already in the knowledge base.",
                tool_name=self.name,
            )

        # Extract metadata from prior search results
        search_data = prior_search.get("data", {})
        search_papers = search_data.get("papers", []) if isinstance(search_data, dict) else []

        # Build a lookup from arxiv_id to search result metadata
        search_lookup: dict[str, dict] = {}
        for p in search_papers:
            if isinstance(p, dict) and p.get("arxiv_id"):
                search_lookup[p["arxiv_id"]] = p

        papers: list[IngestProposalPaper] = []
        for aid in remaining_ids:
            meta = search_lookup.get(aid, {})
            papers.append(IngestProposalPaper(
                arxiv_id=aid,
                title=meta.get("title", "Unknown"),
                authors=meta.get("authors", []),
                abstract=meta.get("abstract", ""),
                published_date=meta.get("published_date"),
                pdf_url=meta.get("pdf_url", f"https://arxiv.org/pdf/{aid}.pdf"),
            ))

        log.info(
            "propose_ingest",
            proposed=len(papers),
            filtered=len(arxiv_ids) - len(remaining_ids),
        )

        return ToolResult(
            success=True,
            data={
                "papers": [p.model_dump() for p in papers],
                "proposed_ids": remaining_ids,
            },
            prompt_text=_format_proposal_summary(papers),
            tool_name=self.name,
        )
