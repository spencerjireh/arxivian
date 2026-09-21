"""Tests for services/feed_service/derive.py and digest.py: verdict, signals, composite, confidence."""

from datetime import date
from types import SimpleNamespace

import pytest

from src.services.feed_service.derive import (
    build_scores,
    build_signals,
    build_verdict,
    compute_match,
    low_confidence_dimensions,
    parse_dimensions,
    resolve_weights,
)
from src.services.feed_service.digest import CompositeWeights, week_start_for


def _dim(name, level, max_level, *, confidence=0.8, judgments=()):
    probs = {str(i): 0.0 for i in range(max_level + 1)}
    probs[str(level)] = 1.0
    return {
        "dimension": name,
        "level": level,
        "max_level": max_level,
        "expected": float(level),
        "probabilities": probs,
        "confidence": confidence,
        "judgments": list(judgments),
        "evidence": [],
        "reasoning": "",
    }


def _noul(key, p):
    return {
        "key": key,
        "kind": "noul",
        "answer": p >= 0.5,
        "probabilities": {"yes": p, "no": 1 - p},
        "confidence": max(p, 1 - p),
        "legend": None,
    }


def _choice(key, answer, p=0.9):
    return {
        "key": key,
        "kind": "choice",
        "answer": answer,
        "probabilities": {answer: p, "other": 1 - p},
        "confidence": p,
        "legend": None,
    }


def _dims(
    *,
    clarity_algo=0.9,
    feas_level=3,
    data_level=1,
    data_access="public benchmark or standard dataset",
):
    return parse_dimensions(
        {
            "method_clarity": _dim(
                "method_clarity", 3, 4, judgments=[_noul("algorithm_given", clarity_algo)]
            ),
            "resource_feasibility": _dim("resource_feasibility", feas_level, 4),
            "data_availability": _dim(
                "data_availability", data_level, 1, judgments=[_choice("data_access", data_access)]
            ),
            "demand": _dim("demand", 2, 2, confidence=1.0),
        }
    )


def _attrs(*, code=0.9, task="machine translation", family="transformer"):
    return {
        "code_released": _noul("code_released", code),
        "task_type": _choice("task_type", task),
        "model_family": _choice("model_family", family),
    }


@pytest.mark.unit
class TestParseDimensions:
    def test_coerces_string_probability_keys(self):
        dims = parse_dimensions({"demand": _dim("demand", 1, 2)})
        assert dims["demand"].probabilities == {0: 0.0, 1: 1.0, 2: 0.0}

    def test_skips_malformed_and_non_dict(self):
        dims = parse_dimensions({"demand": {"bogus": 1}, "x": 3, "ok": _dim("ok", 0, 1)})
        assert set(dims) == {"ok"}

    def test_none_payload(self):
        assert parse_dimensions(None) == {}


@pytest.mark.unit
class TestVerdict:
    def test_full(self):
        assert (
            build_verdict(_dims(), _attrs())
            == "Transformer for machine translation; one consumer GPU; public data"
        )

    def test_family_other(self):
        assert build_verdict(_dims(), _attrs(family="other")).startswith(
            "Method for machine translation;"
        )

    def test_task_other(self):
        assert build_verdict(_dims(), _attrs(task="other")).startswith("Transformer;")

    def test_both_other_and_missing_dims(self):
        assert build_verdict({}, _attrs(task="other", family="other")) == "Method paper"
        assert build_verdict({}, None) == "Method paper"

    def test_unknown_data_label_omitted(self):
        verdict = build_verdict(_dims(data_access="weird"), _attrs())
        assert verdict == "Transformer for machine translation; one consumer GPU"


@pytest.mark.unit
class TestSignals:
    def test_all_true(self):
        s = build_signals(_dims(), _attrs(), "single_gpu")
        assert s.model_dump() == {
            "pseudocode_present": True,
            "public_datasets": True,
            "single_gpu": True,
            "code_released": True,
            "compute_match": True,
        }

    def test_all_false(self):
        s = build_signals(
            _dims(
                clarity_algo=0.2, feas_level=1, data_level=0, data_access="proprietary or private"
            ),
            _attrs(code=0.1),
            None,
        )
        assert s.model_dump() == {
            "pseudocode_present": False,
            "public_datasets": False,
            "single_gpu": False,
            "code_released": False,
            "compute_match": None,
        }

    def test_not_stated_is_not_public(self):
        s = build_signals(_dims(data_access="not stated"), None, None)
        assert s.public_datasets is False

    @pytest.mark.parametrize(
        ("profile", "level", "expected"),
        [
            ("laptop", 3, True),
            ("laptop", 2, False),
            ("single_gpu", 2, True),
            ("single_gpu", 1, False),
            ("cloud", 1, True),
            ("cloud", 0, False),
        ],
    )
    def test_compute_match_boundaries(self, profile, level, expected):
        assert compute_match(_dims(feas_level=level), profile) is expected

    def test_compute_match_without_feasibility_dim(self):
        assert compute_match({}, "laptop") is None


@pytest.mark.unit
class TestConfidence:
    def test_threshold(self):
        dims = parse_dimensions(
            {
                "method_clarity": _dim("method_clarity", 2, 4, confidence=0.49),
                "resource_feasibility": _dim("resource_feasibility", 2, 4, confidence=0.5),
                "data_availability": _dim("data_availability", 1, 1, confidence=0.3),
            }
        )
        assert low_confidence_dimensions(dims) == ["data_availability", "method_clarity"]


@pytest.mark.unit
class TestScoresAndWeights:
    def test_build_scores_renormalizes_null_demand(self):
        score = SimpleNamespace(
            method_clarity_score=80,
            resource_feasibility_score=60,
            data_availability_score=100,
            demand_score=None,
        )
        assert build_scores(score).composite == 70.0

    def test_resolve_weights(self):
        assert resolve_weights(None).demand == 0.30
        assert resolve_weights({"bogus": 1.0}).demand == 0.30
        assert resolve_weights({"method_clarity": 1, "resource_feasibility": 0, "demand": 0}) == (
            CompositeWeights(method_clarity=1, resource_feasibility=0, demand=0)
        )


@pytest.mark.unit
def test_week_start_for():
    assert week_start_for(date(2026, 8, 5)) == date(2026, 8, 3)  # Wednesday -> Monday
    assert week_start_for(date(2026, 8, 3)) == date(2026, 8, 3)
    assert week_start_for(date(2026, 8, 9)) == date(2026, 8, 3)  # Sunday -> previous Monday
