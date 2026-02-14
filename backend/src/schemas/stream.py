"""Streaming request and response schemas with SSE event types."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.common import SourceInfo


class StreamRequest(BaseModel):
    """Request for streaming agent response."""

    query: str = Field(..., description="Question to ask")

    # LLM Provider Selection
    provider: Literal["openai", "nvidia_nim"] | None = Field(
        None, description="LLM provider to use. Uses system default if not specified."
    )
    model: str | None = Field(
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
    max_iterations: int = Field(
        5, ge=1, le=20, description="Maximum router iterations for tool execution"
    )

    # Generation Parameters
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Generation temperature")

    # Request Lifecycle Parameters
    timeout_seconds: int | None = Field(
        None,
        ge=10,
        le=600,
        description="Request timeout in seconds. Uses server default if not specified.",
    )

    # Conversation Parameters
    session_id: str | None = Field(None, description="Session UUID for conversation continuity")
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
    details: dict | None = Field(
        default=None, description="Optional extra info (score, attempt number, etc.)"
    )


class ContentEventData(BaseModel):
    """Data for content events with streaming tokens."""

    token: str = Field(..., description="Generated token")


class SourcesEventData(BaseModel):
    """Data for sources event with retrieved documents."""

    sources: list[SourceInfo] = Field(..., description="Retrieved document sources")


class MetadataEventData(BaseModel):
    """Data for metadata event with execution stats."""

    query: str
    execution_time_ms: float
    retrieval_attempts: int
    rewritten_query: str | None = None
    guardrail_score: int | None = None
    provider: str
    model: str
    session_id: str | None = None
    turn_number: int = 0
    reasoning_steps: list[str] = Field(default_factory=list)
    trace_id: str | None = None  # Langfuse trace ID for feedback


class ErrorEventData(BaseModel):
    """Data for error events."""

    error: str = Field(..., description="Error message")
    code: str | None = Field(default=None, description="Error code if available")


class StreamEvent(BaseModel):
    """SSE event wrapper with event type and data."""

    event: StreamEventType
    data: (
        StatusEventData
        | ContentEventData
        | SourcesEventData
        | MetadataEventData
        | ErrorEventData
        | dict
    )
