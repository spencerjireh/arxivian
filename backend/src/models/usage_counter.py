"""Usage counter model for daily rate limiting."""

import uuid
from sqlalchemy import Column, Integer, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from src.database import Base


class UsageCounter(Base):
    """Daily usage counter per user for rate limiting."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_usage_counters_user_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, server_default=func.current_date())
    query_count = Column(Integer, nullable=False, server_default="0")

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<UsageCounter(user_id='{self.user_id}', date='{self.usage_date}', "
            f"queries={self.query_count})>"
        )
