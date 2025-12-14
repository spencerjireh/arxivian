"""Initial schema with papers, chunks, and ingestion_logs tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-12-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create papers table
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("arxiv_id", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSON(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("categories", postgresql.JSON(), nullable=False),
        sa.Column("published_date", sa.TIMESTAMP(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("sections", postgresql.JSON(), nullable=True),
        sa.Column("references", postgresql.JSON(), nullable=True),
        sa.Column("pdf_processed", sa.Boolean(), default=False),
        sa.Column("pdf_processing_date", sa.TIMESTAMP(), nullable=True),
        sa.Column("parser_used", sa.String(50), nullable=True),
        sa.Column("parser_metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for papers
    op.create_index("idx_papers_arxiv_id", "papers", ["arxiv_id"])
    op.create_index(
        "idx_papers_published_date",
        "papers",
        ["published_date"],
        postgresql_ops={"published_date": "DESC"},
    )
    op.create_index(
        "idx_papers_categories", "papers", ["categories"], postgresql_using="gin"
    )
    op.create_index(
        "idx_papers_processed",
        "papers",
        ["pdf_processed"],
        postgresql_where=sa.text("pdf_processed = false"),
    )

    # Create chunks table
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("arxiv_id", sa.String(50), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_name", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
    )

    # Create indexes for chunks
    op.create_index("idx_chunks_paper_id", "chunks", ["paper_id"])
    op.create_index("idx_chunks_arxiv_id", "chunks", ["arxiv_id"])
    op.create_index(
        "idx_chunks_paper_chunk_unique",
        "chunks",
        ["paper_id", "chunk_index"],
        unique=True,
    )

    # Create HNSW index for vector similarity
    op.execute("""
        CREATE INDEX idx_chunks_embedding ON chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Create full-text search index (tsvector)
    op.execute("""
        ALTER TABLE chunks ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
    """)
    op.create_index(
        "idx_chunks_search_vector", "chunks", ["search_vector"], postgresql_using="gin"
    )

    # Create ingestion_logs table
    op.create_table(
        "ingestion_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_params", postgresql.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("papers_fetched", sa.Integer(), default=0),
        sa.Column("papers_processed", sa.Integer(), default=0),
        sa.Column("chunks_created", sa.Integer(), default=0),
        sa.Column("started_at", sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
    )

    # Create indexes for ingestion_logs
    op.create_index("idx_ingestion_logs_status", "ingestion_logs", ["status"])
    op.create_index(
        "idx_ingestion_logs_started_at",
        "ingestion_logs",
        ["started_at"],
        postgresql_ops={"started_at": "DESC"},
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("ingestion_logs")
    op.drop_table("chunks")
    op.drop_table("papers")
    op.execute("DROP EXTENSION IF EXISTS vector")
