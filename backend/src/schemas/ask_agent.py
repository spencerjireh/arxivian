"""Agent request and response schemas."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from src.schemas.common import SourceInfo


class AgentAskRequest(BaseModel):
    """Request for agent-based question answering."""

    query: str = Field(..., description="Question to ask")

    # LLM Provider Selection
    provider: Optional[Literal["openai", "zai"]] = Field(
        None,
        description="LLM provider to use. Uses system default if not specified."
    )
    model: Optional[str] = Field(
        None,
        description="Model to use. Uses provider's default if not specified."
    )

    # Agent Parameters
    top_k: int = Field(3, ge=1, le=10, description="Number of chunks to retrieve")
    guardrail_threshold: int = Field(
        75, ge=0, le=100, description="Minimum score for query relevance"
    )
    max_retrieval_attempts: int = Field(
        3, ge=1, le=5, description="Maximum query rewriting attempts"
    )

    # Generation Parameters
    temperature: float = Field(
        0.3, ge=0.0, le=1.0, description="Generation temperature"
    )


class AgentAskResponse(BaseModel):
    """Response from agent-based workflow."""

    query: str
    answer: str
    sources: List[SourceInfo]

    # Agent workflow metadata
    reasoning_steps: List[str]
    retrieval_attempts: int
    rewritten_query: Optional[str]
    guardrail_score: int

    # Execution metadata
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    execution_time_ms: float
