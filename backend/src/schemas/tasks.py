"""Schemas for background task operations."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class AsyncTaskResponse(BaseModel):
    """Response when a task is queued."""

    task_id: str = Field(..., description="Unique identifier for the queued task")
    status: Literal["queued"] = Field("queued", description="Initial task status")


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""

    task_id: str = Field(..., description="Unique identifier for the task")
    status: Literal["pending", "started", "success", "failure", "retry"] = Field(
        ..., description="Current task status"
    )
    ready: bool = Field(..., description="Whether the task has completed (success or failure)")
    result: Optional[dict] = Field(
        None, description="Task result if completed successfully (only included on success)"
    )
    error: Optional[str] = Field(
        None, description="Error message if task failed (only included on failure)"
    )
