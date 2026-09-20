"""Tests for the paper-state request validation."""

import pytest

from src.schemas.paper_states import UserPaperStateRequest


@pytest.mark.unit
class TestStateRequest:
    def test_shipped_requires_repo_url(self):
        with pytest.raises(ValueError):
            UserPaperStateRequest(state="shipped")
        assert UserPaperStateRequest(state="shipped", repo_url="https://github.com/a/b").state

    def test_dismissal_reason_only_with_dismissed(self):
        with pytest.raises(ValueError):
            UserPaperStateRequest(state="saved", dismissal_reason="x")
        assert (
            UserPaperStateRequest(state="dismissed", dismissal_reason="x").dismissal_reason == "x"
        )
