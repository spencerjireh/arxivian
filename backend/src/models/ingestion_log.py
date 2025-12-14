"""Ingestion log model for tracking ingestion jobs."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base


class IngestionLog(Base):
    """Track ingestion jobs for observability."""

    __tablename__ = "ingestion_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job metadata
    query_params = Column(JSON, nullable=False)  # What was requested
    status = Column(
        String(20), nullable=False, index=True
    )  # 'running', 'completed', 'failed'

    # Results
    papers_fetched = Column(Integer, default=0)
    papers_processed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)

    # Timing
    started_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    duration_seconds = Column(Numeric, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    def __repr__(self):
        return f"<IngestionLog(status='{self.status}', papers_fetched={self.papers_fetched})>"
