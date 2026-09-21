"""Streaming request and response schemas with SSE event types."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class SourceInfo(BaseModel):
    """A retrieved source paper, as sent in the SOURCES event."""

    arxiv_id: str
    title: str
    authors: list[str]
    pdf_url: str
    relevance_score: float
    published_date: str | None = None
    was_graded_relevant: bool | None = None


class StreamRequest(BaseModel):
    """Request for one turn of a paper-scoped conversation.

    Every conversation is scoped to one ingested paper (Phase 3). The scope is persisted on
    the conversation, so a follow-up that names a different paper is a 409.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, description="Question to ask")
    arxiv_id: str = Field(..., description="The ingested paper this conversation is scoped to")
    session_id: str | None = Field(None, description="Session UUID for conversation continuity")


# SSE Event Types


class StreamEventType(StrEnum):
    """Types of SSE events emitted during streaming."""

    STATUS = "status"  # Workflow step updates (classify, execute, evaluate, generate)
    CONTENT = "content"  # Streaming answer tokens
    SOURCES = "sources"  # Retrieved document sources
    METADATA = "metadata"  # Final execution metadata
    ERROR = "error"  # Error events
    DONE = "done"  # Stream complete
    CITATIONS = "citations"  # Citation graph from explore_citations tool


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
    guardrail_score: int | None = None
    session_id: str | None = None
    turn_number: int = 0


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
    )
