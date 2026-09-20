"""Unit tests for the rubric v2 combine rules and the DimensionScore derived values."""

import pytest

from src.clients.typesafe_client import ChoiceResult, ScoreResult
from src.schemas.scoring_state import (
    DEMAND_BAND_TO_SCORE,
    DimensionScore,
    score_to_band,
)
from src.services.scoring_service.judgments import (
    argmax,
    combine_data_availability,
    combine_method_clarity,
    combine_resource_feasibility,
    demand_from_band,
    noul_judgment,
    poisson_binomial,
    score_judgment,
)
from src.services.scoring_service.questions import GATE_PASS_OPTIONS, METHOD_CLARITY_CRITERIA


class TestPoissonBinomial:
    def test_all_certain(self):
        assert poisson_binomial([1, 1, 1, 1]) == {0: 0, 1: 0, 2: 0, 3: 0, 4: 1.0}

    def test_fair_coins(self):
        dist = poisson_binomial([0.5] * 4)
        assert dist[2] == pytest.approx(0.375)
        assert dist[0] == pytest.approx(0.0625)

    def test_sums_to_one(self):
        dist = poisson_binomial([0.1, 0.9, 0.33, 0.7])
        assert sum(dist.values()) == pytest.approx(1.0, abs=1e-5)
        assert list(dist) == [0, 1, 2, 3, 4]

    def test_empty(self):
        assert poisson_binomial([]) == {0: 1.0}


class TestArgmax:
    def test_tie_resolves_lower(self):
        assert argmax({0: 0.1, 1: 0.45, 2: 0.45}) == 1


class TestJudgmentBuilders:
    def test_noul_majority_and_confidence(self):
        j = noul_judgment("x", 0.3)
        assert j.answer is False
        assert j.probabilities == {"yes": 0.3, "no": 0.7}
        assert j.confidence == 0.7

    def test_noul_clamps(self):
        assert noul_judgment("x", 1.4).probabilities["yes"] == 1.0

    def test_score_judgment_string_keys(self):
        j = score_judgment(
            "tier",
            ScoreResult(
                score=2.5,
                probabilities={0: 0.0, 1: 0.5, 2: 0.5},
                confidence=0.5,
                legend=["a", "b", "c"],
            ),
        )
        assert j.answer == 1
        assert list(j.probabilities) == ["0", "1", "2"]
        assert j.legend == ["a", "b", "c"]


class TestCombineMethodClarity:
    def test_distribution_and_derived(self):
        nouls = dict(zip(METHOD_CLARITY_CRITERIA, [0.9, 0.9, 0.9, 0.9], strict=False))
        dim = combine_method_clarity(nouls, METHOD_CLARITY_CRITERIA, [])
        assert dim.max_level == 4
        assert dim.expected == pytest.approx(3.6)
        assert dim.level == 4
        assert dim.confidence == pytest.approx(0.6561)
        assert dim.derived_score() == 90
        assert dim.band() == "HIGH"
        assert "4 of 4" in dim.reasoning

    def test_mixed_criteria_lands_mid(self):
        nouls = dict(zip(METHOD_CLARITY_CRITERIA, [0.95, 0.9, 0.2, 0.1], strict=False))
        dim = combine_method_clarity(nouls, METHOD_CLARITY_CRITERIA, [])
        assert dim.level == 2
        assert dim.derived_score() == 54
        assert dim.band() == "MED"


class TestCombineResourceFeasibility:
    def test_uses_score_distribution(self):
        tier = ScoreResult(
            score=0.6,
            probabilities={0: 0.5, 1: 0.4, 2: 0.1},
            confidence=0.5,
            legend=["Cluster: x", "Node: y", "GPU: z"],
        )
        dim = combine_resource_feasibility(tier, {"compute_stated": 0.9}, [])
        assert dim.level == 0
        assert dim.probabilities == {0: 0.5, 1: 0.4, 2: 0.1, 3: 0.0, 4: 0.0}
        assert dim.derived_score() == 15
        assert dim.band() == "LOW"
        assert dim.judgments[0].kind == "score"
        assert dim.judgments[1].key == "compute_stated"
        assert "Cluster" in dim.reasoning


class TestCombineDataAvailability:
    def test_pass_mass_groups_options(self):
        access = ChoiceResult(
            choice="not stated",
            probabilities={
                "not stated": 0.4,
                "public benchmark or standard dataset": 0.3,
                "proprietary or private": 0.3,
            },
            confidence=0.4,
        )
        dim = combine_data_availability(access, GATE_PASS_OPTIONS, [])
        assert dim.level == 1
        assert dim.probabilities[1] == pytest.approx(0.7)
        assert dim.derived_score() == 100
        assert dim.reasoning.startswith("PASS")

    def test_fail_on_inaccessible_majority(self):
        access = ChoiceResult(
            choice="available on request or under license",
            probabilities={"available on request or under license": 0.55, "not stated": 0.45},
            confidence=0.55,
        )
        dim = combine_data_availability(access, GATE_PASS_OPTIONS, [])
        assert dim.level == 0
        assert dim.derived_score() == 0
        assert dim.confidence == pytest.approx(0.55)


class TestDemand:
    @pytest.mark.parametrize("band", ["LOW", "MED", "HIGH"])
    def test_one_hot(self, band):
        dim = demand_from_band(band, [], "r")
        assert dim.derived_score() == DEMAND_BAND_TO_SCORE[band]
        assert sum(dim.probabilities.values()) == 1.0
        assert dim.confidence == 1.0


class TestDimensionScoreJsonb:
    def test_round_trip_coerces_string_keys(self):
        dim = demand_from_band("HIGH", [], "r")
        payload = dim.model_dump(mode="json")
        assert list(payload["probabilities"]) == ["0", "1", "2"]
        back = DimensionScore.from_jsonb(payload)
        assert back == dim
        assert back.probabilities[2] == 1.0

    def test_bands(self):
        assert score_to_band(39) == "LOW"
        assert score_to_band(40) == "MED"
        assert score_to_band(70) == "HIGH"
