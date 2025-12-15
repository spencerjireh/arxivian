"""Chunk model for text chunks with embeddings."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from pgvector.sqlalchemy import Vector
from src.database import Base


class Chunk(Base):
    """Text chunk with embedding for retrieval."""

    __tablename__ = "chunks"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to papers
    paper_id = Column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    arxiv_id = Column(String(50), nullable=False, index=True)  # Denormalized for faster queries

    # Chunk content
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within paper (0-based)

    # Chunk metadata
    section_name = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)

    # Embedding (1024 dimensions for Jina v3)
    embedding = Column(Vector(1024), nullable=False)

    # Full-text search vector (generated column)
    search_vector = Column(TSVECTOR)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())

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
