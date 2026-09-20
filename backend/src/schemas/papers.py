"""Schemas for the ops papers endpoints."""

from pydantic import BaseModel


class DeletePaperResponse(BaseModel):
    """Response for delete paper endpoint."""

    arxiv_id: str
    title: str
    chunks_deleted: int
    message: str = "Paper and associated chunks deleted successfully"
