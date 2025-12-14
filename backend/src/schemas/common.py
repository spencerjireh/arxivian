"""Common schemas used across the application."""

from typing import List, Optional
from pydantic import BaseModel


class SourceInfo(BaseModel):
    """Information about a source document."""

    arxiv_id: str
    title: str
    authors: List[str]
    pdf_url: str
    relevance_score: float
    published_date: Optional[str] = None
    was_graded_relevant: Optional[bool] = None


class ChunkInfo(BaseModel):
    """Information about a chunk."""

    chunk_id: str
    arxiv_id: str
    title: str
    chunk_text: str
    section_name: Optional[str] = None
    score: float
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
