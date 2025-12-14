"""Search request and response schemas."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from src.schemas.common import ChunkInfo


class DateRange(BaseModel):
    """Date range filter."""

    start: str = Field(..., description="Start date (YYYY-MM-DD)")
    end: str = Field(..., description="End date (YYYY-MM-DD)")


class SearchRequest(BaseModel):
    """Request for hybrid search."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(10, ge=1, le=50, description="Number of results")
    search_mode: Literal["vector", "fulltext", "hybrid"] = Field(
        "hybrid", description="Search mode"
    )
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relevance score")
    categories: Optional[List[str]] = Field(None, description="Filter by arXiv categories")
    date_range: Optional[DateRange] = Field(None, description="Filter by date range")


class SearchResponse(BaseModel):
    """Response from search."""

    query: str
    total: int
    results: List[ChunkInfo]
    search_mode: str
    execution_time_ms: float
