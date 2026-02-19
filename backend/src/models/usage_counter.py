"""Usage counter model for daily rate limiting."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Integer, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class UsageCounter(Base):
    """Daily usage counter per user for rate limiting."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_usage_counters_user_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    query_count: Mapped[int] = mapped_column(Integer, server_default="0")
    ingest_count: Mapped[int] = mapped_column(Integer, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<UsageCounter(user_id='{self.user_id}', date='{self.usage_date}', "
            f"queries={self.query_count}, ingests={self.ingest_count})>"
        )
