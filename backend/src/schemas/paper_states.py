"""PUT/DELETE /papers/{arxiv_id}/state schemas (routers/paper_states.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

PaperState = Literal["saved", "dismissed", "implementing", "shipped"]


class UserPaperStateResponse(BaseModel):
    """A user's lifecycle state for one paper."""

    model_config = ConfigDict(from_attributes=True)

    state: PaperState
    repo_url: str | None = None
    dismissal_reason: str | None = None
    updated_at: datetime


class UserPaperStateRequest(BaseModel):
    """PUT /papers/{arxiv_id}/state body."""

    model_config = ConfigDict(extra="forbid")

    state: PaperState
    repo_url: HttpUrl | None = None
    dismissal_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check_fields_for_state(self) -> UserPaperStateRequest:
        if self.state == "shipped" and self.repo_url is None:
            raise ValueError("repo_url is required when state is 'shipped'")
        if self.state != "dismissed" and self.dismissal_reason is not None:
            raise ValueError("dismissal_reason is only allowed when state is 'dismissed'")
        return self
