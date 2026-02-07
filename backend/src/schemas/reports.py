"""Schemas for report operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    """Response for a single report."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Report ID")
    report_type: str = Field(..., description="Type of report")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    data: dict[str, Any] = Field(..., description="Report data")
    created_at: datetime = Field(..., description="When the report was created")


class ReportListResponse(BaseModel):
    """Response for listing reports."""

    reports: list[ReportResponse]
    total: int = Field(..., description="Total number of reports")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")
