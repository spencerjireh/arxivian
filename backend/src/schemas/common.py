"""Common schemas used across the application."""

from pydantic import BaseModel


class SourceInfo(BaseModel):
    """Information about a source document."""

    arxiv_id: str
    title: str
    authors: list[str]
    pdf_url: str
    relevance_score: float
    published_date: str | None = None
    was_graded_relevant: bool | None = None


class ChunkInfo(BaseModel):
    """Information about a chunk."""

    chunk_id: str
    arxiv_id: str
    title: str
    chunk_text: str
    section_name: str | None = None
    score: float
    vector_score: float | None = None
    text_score: float | None = None
