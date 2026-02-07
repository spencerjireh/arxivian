"""Schemas for background task operations."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class AsyncTaskResponse(BaseModel):
    """Response when a task is queued."""

    task_id: str = Field(..., description="Unique identifier for the queued task")
    status: Literal["queued"] = Field("queued", description="Initial task status")
    task_type: str = Field(..., description="Type of the queued task")


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""

    task_id: str = Field(..., description="Unique identifier for the task")
    status: Literal["queued", "pending", "started", "success", "failure", "retry", "revoked"] = (
        Field(..., description="Current task status")
    )
    ready: bool = Field(..., description="Whether the task has completed (success or failure)")
    result: Optional[dict] = Field(
        None, description="Task result if completed successfully (only included on success)"
    )
    error: Optional[str] = Field(
        None, description="Error message if task failed (only included on failure)"
    )
    task_type: Optional[str] = Field(None, description="Type of the task")
    created_at: Optional[datetime] = Field(None, description="When the task was created")


class TaskListItem(BaseModel):
    """Single task in a task list response."""

    model_config = ConfigDict(from_attributes=True)

    task_id: str = Field(..., description="Celery task ID", validation_alias="celery_task_id")
    task_type: str = Field(..., description="Type of the task")
    status: str = Field(..., description="Current task status")
    error: Optional[str] = Field(
        None, description="Error message if task failed", validation_alias="error_message"
    )
    created_at: datetime = Field(..., description="When the task was created")
    completed_at: Optional[datetime] = Field(None, description="When the task completed")


class TaskListResponse(BaseModel):
    """Response for listing tasks."""

    tasks: list[TaskListItem]
    total: int = Field(..., description="Total number of tasks")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class RevokeTaskResponse(BaseModel):
    """Response when a task is revoked."""

    task_id: str = Field(..., description="ID of the revoked task")
    revoked: bool = Field(..., description="Whether the revoke was sent")
    terminated: bool = Field(..., description="Whether termination was requested")
