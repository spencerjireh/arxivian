"""Schemas for papers management endpoints."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaperResponseBase(BaseModel):
    """Base paper response without raw_text."""

    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_date: datetime
    pdf_url: str
    sections: list[dict] | None = None
    pdf_processed: bool
    pdf_processing_date: datetime | None = None
    parser_used: str | None = None
    created_at: datetime
    updated_at: datetime


class PaperResponse(PaperResponseBase):
    """Full paper response including raw_text."""

    raw_text: str | None = None


class PaperListItem(PaperResponseBase):
    """Paper item for list responses (excludes raw_text)."""


class PaperListResponse(BaseModel):
    """Response for list papers endpoint."""

    total: int
    offset: int
    limit: int
    papers: list[PaperListItem]


class DeletePaperResponse(BaseModel):
    """Response for delete paper endpoint."""

    arxiv_id: str
    title: str
    chunks_deleted: int
    message: str = "Paper and associated chunks deleted successfully"
