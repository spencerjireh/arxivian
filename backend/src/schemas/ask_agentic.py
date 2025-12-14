"""Agentic RAG request and response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from src.schemas.common import SourceInfo


class AgenticAskRequest(BaseModel):
    """Request for agentic RAG with LangGraph."""

    query: str = Field(..., description="Question to ask")
    model: str = Field("gpt-4o-mini", description="OpenAI model to use")
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    max_retrieval_attempts: int = Field(
        3, ge=1, le=5, description="Maximum query rewrite attempts"
    )
    guardrail_threshold: int = Field(
        75, ge=0, le=100, description="Minimum score to proceed (0-100)"
    )
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Generation temperature")


class AgenticAskResponse(BaseModel):
    """Response from agentic RAG with reasoning."""

    query: str
    answer: str
    sources: List[SourceInfo]
    reasoning_steps: List[str]
    retrieval_attempts: int
    rewritten_query: Optional[str] = None
    guardrail_score: int
    execution_time_ms: float
