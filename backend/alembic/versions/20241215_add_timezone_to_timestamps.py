"""Add timezone to all timestamp columns.

Revision ID: 002_add_timezone
Revises: 001_initial
Create Date: 2024-12-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_timezone"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert TIMESTAMP columns to TIMESTAMP WITH TIME ZONE."""

    # Papers table - convert all timestamp columns
    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN published_date TYPE TIMESTAMP WITH TIME ZONE 
        USING published_date AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN pdf_processing_date TYPE TIMESTAMP WITH TIME ZONE 
        USING pdf_processing_date AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
        USING updated_at AT TIME ZONE 'UTC'
    """)

    # Chunks table - convert timestamp column
    op.execute("""
        ALTER TABLE chunks 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    """Convert TIMESTAMP WITH TIME ZONE columns back to TIMESTAMP."""

    # Papers table - convert all timestamp columns back
    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN published_date TYPE TIMESTAMP WITHOUT TIME ZONE 
        USING published_date AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN pdf_processing_date TYPE TIMESTAMP WITHOUT TIME ZONE 
        USING pdf_processing_date AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE 
        USING created_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE papers 
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE 
        USING updated_at AT TIME ZONE 'UTC'
    """)

    # Chunks table - convert timestamp column back
    op.execute("""
        ALTER TABLE chunks 
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE 
        USING created_at AT TIME ZONE 'UTC'
    """)
