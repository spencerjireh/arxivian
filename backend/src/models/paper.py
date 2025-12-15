"""Paper model for arXiv papers."""

import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base


class Paper(Base):
    """arXiv paper metadata and content."""

    __tablename__ = "papers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # arXiv metadata
    arxiv_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    authors = Column(JSONB, nullable=False)  # List of author names
    abstract = Column(Text, nullable=False)
    categories = Column(JSONB, nullable=False)  # List of arXiv categories
    published_date = Column(TIMESTAMP, nullable=False, index=True)
    pdf_url = Column(Text, nullable=False)

    # Parsed content
    raw_text = Column(Text, nullable=True)
    sections = Column(JSONB, nullable=True)  # List of {title, content, page_start, page_end}
    references = Column(JSONB, nullable=True)  # List of citation strings

    # Processing metadata
    pdf_processed = Column(Boolean, default=False, index=True)
    pdf_processing_date = Column(TIMESTAMP, nullable=True)
    parser_used = Column(String(50), nullable=True)
    parser_metadata = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Paper(arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"
