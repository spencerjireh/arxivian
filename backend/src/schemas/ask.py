"""RAG request and response schemas."""

from typing import List, Literal
from pydantic import BaseModel, Field
from src.schemas.common import SourceInfo


class AskRequest(BaseModel):
    """Request for standard RAG question answering."""

    query: str = Field(..., description="Question to ask")
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    search_mode: Literal["vector", "fulltext", "hybrid"] = Field(
        "hybrid", description="Search mode"
    )
    model: str = Field("gpt-4o-mini", description="OpenAI model to use")
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Generation temperature")
    max_tokens: int = Field(1000, ge=100, le=4000, description="Maximum tokens to generate")


class AskResponse(BaseModel):
    """Response from standard RAG."""

    query: str
    answer: str
    sources: List[SourceInfo]
    chunks_used: int
    search_mode: str
    model: str
    execution_time_ms: float


class StreamRequest(BaseModel):
    """Request for streaming RAG."""

    query: str = Field(..., description="Question to ask")
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    search_mode: Literal["vector", "fulltext", "hybrid"] = Field(
        "hybrid", description="Search mode"
    )
    model: str = Field("gpt-4o-mini", description="OpenAI model to use")
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Generation temperature")
