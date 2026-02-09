"""Schemas for user preferences."""

from typing import Optional
from pydantic import BaseModel, Field


class ArxivSearchConfig(BaseModel):
    """Configuration for a saved arXiv search."""

    name: str = Field(..., description="Display name for this search", max_length=100)
    query: str = Field(..., description="arXiv search query", min_length=1, max_length=500)
    categories: Optional[list[str]] = Field(
        None, description="arXiv categories to filter (e.g., cs.AI, cs.LG)"
    )
    max_results: int = Field(10, ge=1, le=50, description="Maximum papers to fetch per run")
    enabled: bool = Field(True, description="Whether this search is active for scheduled runs")


class NotificationSettings(BaseModel):
    """User notification preferences."""

    email_digest: bool = Field(False, description="Receive weekly email digest")


class UserPreferences(BaseModel):
    """Complete user preferences object."""

    arxiv_searches: list[ArxivSearchConfig] = Field(
        default_factory=list, description="Saved arXiv search configurations"
    )
    notification_settings: NotificationSettings = Field(
        default_factory=NotificationSettings, description="Notification preferences"
    )

    @classmethod
    def from_raw(cls, prefs: dict) -> "UserPreferences":
        """Construct from a raw preferences dict (e.g. from database JSONB)."""
        return cls(
            arxiv_searches=[ArxivSearchConfig(**s) for s in prefs.get("arxiv_searches", [])],
            notification_settings=prefs.get("notification_settings", {}),
        )


class UpdateArxivSearchesRequest(BaseModel):
    """Request to update arXiv searches."""

    arxiv_searches: list[ArxivSearchConfig] = Field(
        ..., description="Complete list of arXiv search configurations"
    )
