"""Ops operation schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class OrphanedPaper(BaseModel):
    """Details of an orphaned paper."""

    arxiv_id: str
    title: str
    paper_id: str


class CleanupResponse(BaseModel):
    """Response from cleanup operation."""

    orphaned_papers_found: int
    papers_deleted: int
    deleted_papers: List[OrphanedPaper]


class UpdateTierRequest(BaseModel):
    """Request to update a user's tier."""

    tier: str  # Validated against UserTier enum in handler


class UpdateTierResponse(BaseModel):
    """Response after tier update."""

    user_id: UUID
    tier: str
    email: Optional[str] = None
