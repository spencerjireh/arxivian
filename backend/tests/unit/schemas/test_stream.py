"""Tests for StreamRequest (paper-scoped, no knobs)."""

import pytest
from pydantic import ValidationError

from src.schemas.stream import StreamRequest


@pytest.mark.unit
class TestStreamRequest:
    def test_query_and_arxiv_id_required(self):
        req = StreamRequest(query="What is attention?", arxiv_id="2301.00001")
        assert req.session_id is None

    def test_missing_arxiv_id_rejected(self):
        with pytest.raises(ValidationError, match="arxiv_id"):
            StreamRequest(query="test")

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            StreamRequest(query="", arxiv_id="2301.00001")

    @pytest.mark.parametrize("knob", ["model", "temperature", "top_k", "resume", "provider"])
    def test_removed_knobs_are_rejected(self, knob):
        with pytest.raises(ValidationError, match=knob):
            StreamRequest(query="q", arxiv_id="2301.00001", **{knob: 1})
