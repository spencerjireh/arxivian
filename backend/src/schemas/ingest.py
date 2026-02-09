"""Ingestion request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request to ingest papers from arXiv."""

    query: str = Field(..., description="arXiv search query")
    max_results: int = Field(10, ge=1, le=50, description="Maximum papers to fetch")
    categories: list[str] | None = Field(None, description="arXiv categories filter")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")
    force_reprocess: bool = Field(False, description="Re-process existing papers")
    idempotency_key: str | None = Field(
        default=None,
        description="Unique key to prevent duplicate processing. If provided, duplicate requests return cached response.",
        max_length=64,
    )


class PaperError(BaseModel):
    """Error information for a failed paper."""

    arxiv_id: str
    error: str


class PaperResult(BaseModel):
    """Result for a single paper."""

    arxiv_id: str
    title: str
    chunks_created: int
    status: Literal["success", "failed"]


class IngestResponse(BaseModel):
    """Response from paper ingestion."""

    status: Literal["completed", "failed"]
    papers_fetched: int
    papers_processed: int
    chunks_created: int
    duration_seconds: float
    errors: list[PaperError] = []
    papers: list[PaperResult] = []
