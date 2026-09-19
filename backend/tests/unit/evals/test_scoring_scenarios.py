"""Consistency checks on the golden-set labels (no LLM, no DB)."""

import pytest

from tests.evals.fixtures.scoring_scenarios import SCORING_SCENARIOS, ScoringScenario

_BAND_RANK = {"LOW": 0, "MED": 1, "HIGH": 2}


def _rubric_implementable(s: ScoringScenario) -> bool:
    return (
        s.data_availability == "PASS"
        and _BAND_RANK[s.method_clarity] >= _BAND_RANK["MED"]
        and _BAND_RANK[s.resource_feasibility] >= _BAND_RANK["MED"]
    )


@pytest.mark.unit
class TestScoringScenarios:
    def test_every_row_is_reviewed(self):
        unreviewed = [s.id for s in SCORING_SCENARIOS if not s.reviewed]
        assert unreviewed == []

    @pytest.mark.parametrize("scenario", SCORING_SCENARIOS, ids=lambda s: s.id)
    def test_implementable_matches_rubric_rule(self, scenario: ScoringScenario):
        assert scenario.implementable == _rubric_implementable(scenario)

    def test_ids_and_arxiv_ids_unique(self):
        ids = [s.id for s in SCORING_SCENARIOS]
        arxiv_ids = [s.arxiv_id for s in SCORING_SCENARIOS]
        assert len(ids) == len(set(ids))
        assert len(arxiv_ids) == len(set(arxiv_ids))

    def test_covers_both_gate_sides_and_low_feasibility(self):
        assert any(s.data_availability == "FAIL" for s in SCORING_SCENARIOS)
        assert any(s.resource_feasibility == "LOW" for s in SCORING_SCENARIOS)
        assert any(s.method_clarity == "LOW" for s in SCORING_SCENARIOS)
