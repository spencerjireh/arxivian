"""Ops operation schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OrphanedPaper(BaseModel):
    """Details of an orphaned paper."""

    arxiv_id: str
    title: str
    paper_id: str


class CleanupResponse(BaseModel):
    """Response from cleanup operation."""

    orphaned_papers_found: int
    papers_deleted: int
    deleted_papers: list[OrphanedPaper]


class UpdateTierRequest(BaseModel):
    """Request to update a user's tier."""

    tier: str  # Validated against UserTier enum in handler


class UpdateTierResponse(BaseModel):
    """Response after tier update."""

    user_id: UUID
    tier: str
    email: str | None = None


class BulkIngestRequest(BaseModel):
    """Request to bulk-ingest papers via ops API."""

    arxiv_ids: list[str] | None = Field(None, description="Specific arXiv IDs to ingest")
    search_query: str | None = Field(None, description="arXiv search query")
    max_results: int = Field(10, ge=1, le=50, description="Max papers for search query")
    categories: list[str] | None = Field(None, description="arXiv categories filter")
    force_reprocess: bool = Field(False, description="Re-process existing papers")

    @model_validator(mode="after")
    def require_ids_or_query(self) -> "BulkIngestRequest":
        if not self.arxiv_ids and not self.search_query:
            raise ValueError("At least one of 'arxiv_ids' or 'search_query' must be provided.")
        return self


class BulkIngestResponse(BaseModel):
    """Response from bulk ingestion."""

    tasks_queued: int
    task_ids: list[str]


class OpsArxivSearchConfig(BaseModel):
    """Configuration for a system-level arXiv search (ops only)."""

    name: str = Field(..., description="Display name for this search", max_length=100)
    query: str = Field(..., description="arXiv search query", min_length=1, max_length=500)
    categories: list[str] | None = Field(
        None, description="arXiv categories to filter (e.g., cs.AI, cs.LG)"
    )
    max_results: int = Field(10, ge=1, le=50, description="Maximum papers to fetch per run")
    enabled: bool = Field(True, description="Whether this search is active for scheduled runs")


class UpdateSystemSearchesRequest(BaseModel):
    """Request to update system arXiv searches."""

    arxiv_searches: list[OpsArxivSearchConfig] = Field(
        ..., description="Complete list of arXiv search configurations"
    )


class SystemSearchesResponse(BaseModel):
    """Response containing system arXiv search configurations."""

    arxiv_searches: list[OpsArxivSearchConfig] = Field(
        default_factory=list, description="System arXiv search configurations"
    )
