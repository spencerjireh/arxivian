"""Unit tests for Stage 1 triage: result schemas and the batched prompt builder."""

import pytest
from pydantic import ValidationError

from src.services.scoring_service.triage import (
    TRIAGE_SYSTEM_PROMPT,
    TriageBatchResult,
    TriageResult,
    get_triage_batch_prompt,
    normalize_arxiv_id,
)


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


class TestGetTriageBatchPrompt:
    def test_returns_system_and_user_tuple(self):
        papers = [{"arxiv_id": "2401.001", "title": "A Method", "abstract": "We propose..."}]
        system, user = get_triage_batch_prompt(papers)
        assert system == TRIAGE_SYSTEM_PROMPT
        assert isinstance(user, str)

    def test_numbers_each_paper_and_echoes_ids(self):
        papers = [
            {"arxiv_id": "2401.001", "title": "One", "abstract": "abs one"},
            {"arxiv_id": "2401.002", "title": "Two", "abstract": "abs two"},
        ]
        _, user = get_triage_batch_prompt(papers)

        assert "1. arxiv_id: 2401.001" in user
        assert "2. arxiv_id: 2401.002" in user
        assert "abs one" in user and "abs two" in user
        assert "2 papers" in user  # batch count stated

    def test_handles_missing_fields(self):
        papers = [{"arxiv_id": "2401.003"}]  # no title/abstract
        _, user = get_triage_batch_prompt(papers)
        assert "arxiv_id: 2401.003" in user
        assert "Unknown title" in user


class TestNormalizeArxivId:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2609.22064", "2609.22064"),
            ("arXiv:2609.22064", "2609.22064"),
            ("ARXIV:2609.22064v2", "2609.22064"),
            (" arXiv:2609.22064v10 ", "2609.22064"),
            ("https://arxiv.org/abs/2609.22064v1", "2609.22064"),
            ("http://www.arxiv.org/pdf/2609.22064v3.pdf", "2609.22064"),
            ("hep-th/9901001v2", "hep-th/9901001"),
            ("arXiv:cs.LG/0701001", "cs.LG/0701001"),
        ],
    )
    def test_reduces_to_the_bare_crawled_form(self, raw, expected):
        assert normalize_arxiv_id(raw) == expected
