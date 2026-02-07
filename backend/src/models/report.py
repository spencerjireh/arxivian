"""Report model for persisting generated reports."""

import uuid
from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class Report(Base):
    """Stores generated reports for later retrieval."""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type = Column(String(100), nullable=False)
    period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    period_end = Column(TIMESTAMP(timezone=True), nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<Report(type='{self.report_type}', period='{self.period_start} - {self.period_end}')>"
        )
