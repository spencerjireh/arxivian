"""Agent execution model for state persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, TIMESTAMP, func, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class AgentExecution(Base):
    """Stores agent execution state for pause/resume functionality."""

    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(
        Enum("running", "paused", "completed", "failed", name="execution_status"),
        default="running",
    )
    state_snapshot: Mapped[dict] = mapped_column(JSONB)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    pause_reason: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<AgentExecution(id='{self.id}', session='{self.session_id}', status='{self.status}')>"
        )
