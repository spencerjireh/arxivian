"""Feedback schemas for Langfuse integration."""

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """User feedback submission."""

    trace_id: str = Field(..., description="Langfuse trace ID from response metadata")
    score: float = Field(..., ge=0, le=1, description="Feedback score (0=negative, 1=positive)")
    comment: str | None = Field(None, max_length=1000, description="Optional feedback comment")


class FeedbackResponse(BaseModel):
    """Feedback submission result."""

    success: bool
    message: str = "Feedback submitted"
