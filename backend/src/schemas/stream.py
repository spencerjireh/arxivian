"""Streaming request and response schemas with SSE event types."""

from enum import Enum
from typing import List, Optional, Literal, Union

from pydantic import BaseModel, Field

from src.schemas.common import SourceInfo


class StreamRequest(BaseModel):
    """Request for streaming agent response."""

    query: str = Field(..., description="Question to ask")

    # LLM Provider Selection
    provider: Optional[Literal["openai", "zai"]] = Field(
        None, description="LLM provider to use. Uses system default if not specified."
    )
    model: Optional[str] = Field(
        None, description="Model to use. Uses provider's default if not specified."
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
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Generation temperature")

    # Conversation Parameters
    session_id: Optional[str] = Field(None, description="Session UUID for conversation continuity")
    conversation_window: int = Field(
        5, ge=1, le=10, description="Number of previous turns to include in context"
    )


# SSE Event Types


class StreamEventType(str, Enum):
    """Types of SSE events emitted during streaming."""

    STATUS = "status"  # Workflow step updates (guardrail, retrieval, grading, generation)
    CONTENT = "content"  # Streaming answer tokens
    SOURCES = "sources"  # Retrieved document sources
    METADATA = "metadata"  # Final execution metadata
    ERROR = "error"  # Error events
    DONE = "done"  # Stream complete


class StatusEventData(BaseModel):
    """Data for status events indicating workflow progress."""

    step: str = Field(..., description="Current workflow step name")
    message: str = Field(..., description="Human-readable status message")
    details: Optional[dict] = Field(
        None, description="Optional extra info (score, attempt number, etc.)"
    )


class ContentEventData(BaseModel):
    """Data for content events with streaming tokens."""

    token: str = Field(..., description="Generated token")


class SourcesEventData(BaseModel):
    """Data for sources event with retrieved documents."""

    sources: List[SourceInfo] = Field(..., description="Retrieved document sources")


class MetadataEventData(BaseModel):
    """Data for metadata event with execution stats."""

    query: str
    execution_time_ms: float
    retrieval_attempts: int
    rewritten_query: Optional[str] = None
    guardrail_score: Optional[int] = None
    provider: str
    model: str
    session_id: Optional[str] = None
    turn_number: int = 0
    reasoning_steps: List[str] = Field(default_factory=list)


class ErrorEventData(BaseModel):
    """Data for error events."""

    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code if available")


class StreamEvent(BaseModel):
    """SSE event wrapper with event type and data."""

    event: StreamEventType
    data: Union[
        StatusEventData, ContentEventData, SourcesEventData, MetadataEventData, ErrorEventData, dict
    ]
