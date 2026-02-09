"""User model for Clerk-synced users."""

import uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from src.database import Base


class User(Base):
    """User synced with Clerk authentication."""

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clerk identity
    clerk_id = Column(String(255), unique=True, nullable=False, index=True)

    # Tier (free / pro)
    tier = Column(String(20), nullable=False, server_default="free")

    # Profile information (from Clerk)
    email = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    profile_image_url = Column(Text, nullable=True)

    # User preferences (notification settings, etc.)
    preferences = Column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")

    def __repr__(self):
        return f"<User(clerk_id='{self.clerk_id}', email='{self.email}')>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or ""
