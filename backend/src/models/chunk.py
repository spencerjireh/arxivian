"""Chunk model for text chunks with embeddings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, Integer, TIMESTAMP, ForeignKey, Index, func, Computed
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from src.database import Base


class Chunk(Base):
    """Text chunk with embedding for retrieval."""

    __tablename__ = "chunks"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to papers
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        index=True,
    )
    arxiv_id: Mapped[str] = mapped_column(String(50), index=True)  # Denormalized for faster queries

    # Chunk content
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)

    # Chunk metadata
    section_name: Mapped[str | None] = mapped_column(String(255))
    page_number: Mapped[int | None] = mapped_column(Integer)
    word_count: Mapped[int | None] = mapped_column(Integer)

    # Embedding (1024 dimensions for Jina v3)
    embedding: Mapped[Any] = mapped_column(Vector(1024))

    # Full-text search vector (generated column - computed by database)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', chunk_text)")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_chunks_paper_chunk_unique", "paper_id", "chunk_index", unique=True),
        Index(
            "idx_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("idx_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<Chunk(arxiv_id='{self.arxiv_id}', chunk_index={self.chunk_index})>"
