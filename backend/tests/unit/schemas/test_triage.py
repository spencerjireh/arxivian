"""Unit tests for the Stage 1 triage schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.triage import TriageBatchResult, TriageResult


class TestTriageResult:
    def test_valid_round_trip(self):
        r = TriageResult(
            arxiv_id="2401.001",
            paper_class="method",
            rough_implementability=75,
            keep=True,
            reasoning="concrete method",
        )
        assert TriageResult.model_validate_json(r.model_dump_json()) == r

    def test_rejects_out_of_range_score(self):
        with pytest.raises(ValidationError):
            TriageResult(
                arxiv_id="x",
                paper_class="method",
                rough_implementability=101,
                keep=True,
                reasoning="",
            )

    def test_rejects_unknown_paper_class(self):
        with pytest.raises(ValidationError):
            TriageResult(
                arxiv_id="x",
                paper_class="editorial",  # not in the Literal
                rough_implementability=50,
                keep=False,
                reasoning="",
            )

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            TriageResult(
                arxiv_id="x",
                paper_class="method",
                rough_implementability=50,
                keep=True,
                reasoning="",
                unexpected="nope",
            )


class TestTriageBatchResult:
    def test_wraps_result_list(self):
        batch = TriageBatchResult(
            results=[
                TriageResult(
                    arxiv_id="2401.001",
                    paper_class="method",
                    rough_implementability=80,
                    keep=True,
                    reasoning="",
                )
            ]
        )
        assert len(batch.results) == 1
        assert TriageBatchResult.model_validate_json(batch.model_dump_json()) == batch
