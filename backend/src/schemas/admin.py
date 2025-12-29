"""Admin operation schemas."""

from typing import List

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
