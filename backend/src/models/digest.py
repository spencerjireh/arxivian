"""Weekly digest snapshot.

A cached candidate ranking snapshot for a given week and category set -- global sub-scores,
NOT a per-user order (the user-weighted composite and compute-profile match are applied at
read time). Lets past weeks render without recomputation. The exact snapshot contents are
finalized in the build_digest_task work (SPE-271); this table just needs to exist. See
`docs/design/scoring-pipeline.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import String, Date, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Digest(Base):
    """Cached candidate ranking snapshot for one week + category set."""

    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    # Sorted-joined categories for uniqueness; the actual list lives in `categories`.
    category_key: Mapped[str] = mapped_column(String(255))
    categories: Mapped[list] = mapped_column(JSONB)
    # Candidate ranking snapshot: ordered paper ids + their global sub-scores.
    ranking: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("week_start", "category_key", name="uq_digests_week_category"),
    )

    def __repr__(self):
        return f"<Digest(week_start='{self.week_start}', category_key='{self.category_key}')>"
