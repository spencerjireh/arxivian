"""Streaming request and response schemas with SSE event types."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field

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
    CITATIONS = "citations"  # Citation graph from explore_citations tool
    CONFIRM_INGEST = "confirm_ingest"  # HITL: propose papers for user confirmation
    HITL_RESUMED = "hitl_resumed"  # HITL: user responded, active processing resumed (internal)
    INGEST_COMPLETE = "ingest_complete"  # HITL: ingestion finished


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


class CitationsEventData(BaseModel):
    """Data for citation graph from explore_citations tool."""

    arxiv_id: str = Field(..., description="arXiv ID of the explored paper")
    title: str = Field(..., description="Title of the explored paper")
    references: list[str] = Field(default_factory=list, description="Reference titles/descriptions")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reference_count(self) -> int:
        """Derived from references list length to prevent mismatches."""
        return len(self.references)


class DoneEventData(BaseModel):
    """Sentinel: stream is complete."""


class HitlResumedEventData(BaseModel):
    """Internal sentinel: active processing resumed after HITL confirmation."""


class IngestProposalPaper(BaseModel):
    """A single paper proposed for ingestion."""

    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    published_date: str | None = None
    pdf_url: str


class ConfirmIngestEventData(BaseModel):
    """Data for HITL ingest confirmation request."""

    papers: list[IngestProposalPaper] = Field(..., description="Papers proposed for ingestion")
    session_id: str = Field(..., description="Session ID for confirmation endpoint")
    thread_id: str = Field(..., description="LangGraph thread ID for checkpoint resume")


class IngestCompleteEventData(BaseModel):
    """Data for ingest completion notification."""

    papers_processed: int = Field(..., description="Number of papers successfully ingested")
    chunks_created: int = Field(..., description="Total chunks created across all papers")
    duration_seconds: float = Field(..., description="Total ingestion time in seconds")
    errors: list[str] = Field(default_factory=list, description="Per-paper error messages")


class StreamEvent(BaseModel):
    """SSE event wrapper with event type and data."""

    event: StreamEventType
    data: (
        StatusEventData
        | ContentEventData
        | SourcesEventData
        | MetadataEventData
        | ErrorEventData
        | CitationsEventData
        | DoneEventData
        | HitlResumedEventData
        | ConfirmIngestEventData
        | IngestCompleteEventData
    )
