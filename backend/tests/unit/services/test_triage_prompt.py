"""Unit tests for the Stage 1 triage prompt builder."""

from src.services.scoring_service.triage_prompt import (
    TRIAGE_SYSTEM_PROMPT,
    get_triage_batch_prompt,
)


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

        assert "1. arXiv:2401.001" in user
        assert "2. arXiv:2401.002" in user
        assert "abs one" in user and "abs two" in user
        assert "2 papers" in user  # batch count stated

    def test_handles_missing_fields(self):
        papers = [{"arxiv_id": "2401.003"}]  # no title/abstract
        _, user = get_triage_batch_prompt(papers)
        assert "arXiv:2401.003" in user
        assert "Unknown title" in user
