"""Schemas for papers management endpoints."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaperResponseBase(BaseModel):
    """Base paper response without raw_text."""

    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published_date: datetime
    pdf_url: str
    sections: Optional[List[dict]] = None
    pdf_processed: bool
    pdf_processing_date: Optional[datetime] = None
    parser_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaperResponse(PaperResponseBase):
    """Full paper response including raw_text."""

    raw_text: Optional[str] = None


class PaperListItem(PaperResponseBase):
    """Paper item for list responses (excludes raw_text)."""


class PaperListResponse(BaseModel):
    """Response for list papers endpoint."""

    total: int
    offset: int
    limit: int
    papers: List[PaperListItem]


class DeletePaperResponse(BaseModel):
    """Response for delete paper endpoint."""

    arxiv_id: str
    title: str
    chunks_deleted: int
    message: str = "Paper and associated chunks deleted successfully"
