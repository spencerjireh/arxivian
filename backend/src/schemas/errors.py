"""Error response schemas for consistent API error handling."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error context")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "ARXIV_API_ERROR",
                    "message": "Failed to fetch papers from arXiv",
                    "details": {"arxiv_id": "2301.12345", "underlying_error": "HTTP 503"},
                },
                "request_id": "req_abc123",
                "timestamp": "2024-12-15T10:30:00Z",
            }
        }
    }
