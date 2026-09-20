"""X-Api-Key ops endpoint schemas (routers/ops.py): maintenance, tasks, tiers, searches."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class DeletePaperResponse(BaseModel):
    """Response for delete paper endpoint."""

    arxiv_id: str
    title: str
    chunks_deleted: int
    message: str = "Paper and associated chunks deleted successfully"


class AsyncTaskResponse(BaseModel):
    """Response when a task is queued."""

    task_id: str = Field(..., description="Unique identifier for the queued task")
    status: Literal["queued"] = Field("queued", description="Initial task status")
    task_type: str = Field(..., description="Type of the queued task")


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""

    task_id: str = Field(..., description="Unique identifier for the task")
    status: Literal["queued", "pending", "started", "success", "failure", "retry", "revoked"] = (
        Field(..., description="Current task status")
    )
    ready: bool = Field(..., description="Whether the task has completed (success or failure)")
    result: dict | None = Field(
        None, description="Task result if completed successfully (only included on success)"
    )
    error: str | None = Field(
        None, description="Error message if task failed (only included on failure)"
    )
    task_type: str | None = Field(None, description="Type of the task")
    created_at: datetime | None = Field(None, description="When the task was created")


class TaskListItem(BaseModel):
    """Single task in a task list response."""

    model_config = ConfigDict(from_attributes=True)

    task_id: str = Field(..., description="Celery task ID", validation_alias="celery_task_id")
    task_type: str = Field(..., description="Type of the task")
    status: str = Field(..., description="Current task status")
    error: str | None = Field(
        None, description="Error message if task failed", validation_alias="error_message"
    )
    created_at: datetime = Field(..., description="When the task was created")
    completed_at: datetime | None = Field(None, description="When the task completed")


class TaskListResponse(BaseModel):
    """Response for listing tasks."""

    tasks: list[TaskListItem]
    total: int = Field(..., description="Total number of tasks")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class RevokeTaskResponse(BaseModel):
    """Response when a task is revoked."""

    task_id: str = Field(..., description="ID of the revoked task")
    revoked: bool = Field(..., description="Whether the revoke was sent")
    terminated: bool = Field(..., description="Whether termination was requested")
