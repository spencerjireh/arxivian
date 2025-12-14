"""Paper model for arXiv papers."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base


class Paper(Base):
    """arXiv paper metadata and content."""

    __tablename__ = "papers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # arXiv metadata
    arxiv_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    authors = Column(JSON, nullable=False)  # List of author names
    abstract = Column(Text, nullable=False)
    categories = Column(JSON, nullable=False)  # List of arXiv categories
    published_date = Column(TIMESTAMP, nullable=False, index=True)
    pdf_url = Column(Text, nullable=False)

    # Parsed content
    raw_text = Column(Text, nullable=True)
    sections = Column(
        JSON, nullable=True
    )  # List of {title, content, page_start, page_end}
    references = Column(JSON, nullable=True)  # List of citation strings

    # Processing metadata
    pdf_processed = Column(Boolean, default=False, index=True)
    pdf_processing_date = Column(TIMESTAMP, nullable=True)
    parser_used = Column(String(50), nullable=True)
    parser_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Paper(arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"
