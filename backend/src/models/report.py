"""Report model for persisting generated reports."""

import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class Report(Base):
    """Stores per-user ingestion summary reports."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("user_id", "report_type", "period_start", name="uq_reports_user_type_start"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    report_type = Column(String(100), nullable=False)
    period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    period_end = Column(TIMESTAMP(timezone=True), nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<Report(type='{self.report_type}', period='{self.period_start} - {self.period_end}')>"
        )
