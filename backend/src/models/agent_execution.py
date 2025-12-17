"""Agent execution model for state persistence."""

import uuid
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, func, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class AgentExecution(Base):
    """Stores agent execution state for pause/resume functionality."""

    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    status = Column(
        Enum("running", "paused", "completed", "failed", name="execution_status"),
        nullable=False,
        default="running",
    )
    state_snapshot = Column(JSONB, nullable=False)
    iteration = Column(Integer, nullable=False, default=0)
    pause_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<AgentExecution(id='{self.id}', session='{self.session_id}', status='{self.status}')>"
        )
