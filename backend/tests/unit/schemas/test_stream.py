"""Tests for StreamRequest model_validator (query vs resume)."""

import pytest
from pydantic import ValidationError

from src.schemas.stream import StreamRequest, IngestConfirmation


class TestStreamRequestValidator:
    """Tests for the exactly_one_of_query_or_resume validator."""

    def test_query_only_is_valid(self):
        req = StreamRequest(query="What is attention?")
        assert req.query == "What is attention?"
        assert req.resume is None

    def test_resume_only_is_valid(self):
        req = StreamRequest(
            resume=IngestConfirmation(
                session_id="sess-1",
                thread_id="sess-1:0",
                approved=True,
                selected_ids=["2301.00001"],
            )
        )
        assert req.query is None
        assert req.resume is not None
        assert req.resume.approved is True

    def test_both_query_and_resume_raises(self):
        with pytest.raises(ValidationError, match="not both"):
            StreamRequest(
                query="test",
                resume=IngestConfirmation(
                    session_id="sess-1",
                    thread_id="sess-1:0",
                    approved=True,
                    selected_ids=[],
                ),
            )

    def test_neither_query_nor_resume_raises(self):
        with pytest.raises(ValidationError, match="Provide either"):
            StreamRequest()

    def test_resume_decline_with_empty_selected_ids_is_valid(self):
        req = StreamRequest(
            resume=IngestConfirmation(
                session_id="sess-1",
                thread_id="sess-1:0",
                approved=False,
                selected_ids=[],
            )
        )
        assert req.resume.approved is False
        assert req.resume.selected_ids == []
