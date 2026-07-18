"""Per-user paper lifecycle state.

Tracks each user's relationship to a paper: saved / dismissed / implementing / shipped.
One row per (user, paper), updated in place on state transitions. Dismissals with an
optional reason double as labeled feedback for the scoring eval. See
`docs/design/scoring-pipeline.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class UserPaperState(Base):
    """A user's lifecycle state for a paper (saved / dismissed / implementing / shipped)."""

    __tablename__ = "user_paper_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        index=True,
    )
    state: Mapped[str] = mapped_column(String(20), server_default="saved")
    repo_url: Mapped[str | None] = mapped_column(Text)  # set when shipped
    dismissal_reason: Mapped[str | None] = mapped_column(Text)  # optional labeled feedback
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="uq_user_paper_states_user_paper"),
    )

    def __repr__(self):
        return f"<UserPaperState(user_id='{self.user_id}', paper_id='{self.paper_id}', state='{self.state}')>"
