"""TaskExecution model for tracking Celery task ownership and status."""

import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class TaskExecution(Base):
    """Tracks Celery task ownership and status for authenticated endpoints."""

    __tablename__ = "task_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    celery_task_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, server_default="queued")
    error_message = Column(Text, nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TaskExecution(celery_task_id='{self.celery_task_id}', status='{self.status}')>"
