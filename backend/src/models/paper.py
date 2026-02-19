"""Paper model for arXiv papers."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Paper(Base):
    """arXiv paper metadata and content."""

    __tablename__ = "papers"
    __table_args__ = (UniqueConstraint("arxiv_id", name="uq_papers_arxiv_id"),)

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Audit
    ingested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # arXiv metadata
    arxiv_id: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[list] = mapped_column(JSONB)
    abstract: Mapped[str] = mapped_column(Text)
    categories: Mapped[list] = mapped_column(JSONB)
    published_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), index=True)
    pdf_url: Mapped[str] = mapped_column(Text)

    # Parsed content
    raw_text: Mapped[str | None] = mapped_column(Text)
    sections: Mapped[list | None] = mapped_column(JSONB)
    references: Mapped[list | None] = mapped_column(JSONB)

    # Processing metadata
    pdf_processed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", index=True
    )
    pdf_processing_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    parser_used: Mapped[str | None] = mapped_column(String(50))
    parser_metadata: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Paper(arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"
