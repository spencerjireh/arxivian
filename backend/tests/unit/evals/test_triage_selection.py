"""Stage 1 selection eval: the metric math, the label fixture, and the measurement.

Three separate concerns, deliberately not merged:

* `TestSelectionMetrics` exercises the weighting and the derived figures against synthetic
  data. It always runs. The stratified weighting is the part that is easy to get silently
  wrong -- rejects are oversampled by roughly 8x, so an unweighted rate would be badly
  biased -- and a wrong weight produces a plausible-looking number rather than an error.
* `TestTriageSelectionLabels` guards the committed fixture, mirroring
  `test_scoring_scenarios.py`. Skips until labels exist.
* `TestSelectionReport` prints the measurement. Run it with `-s` or you will see nothing.

The report is **not gated yet, on purpose**. A threshold invented before any data exists
would either be met trivially or fail for no reason; the gate goes in once there is a first
number to set it against. See `triage_selection.py` for what the figures mean.
"""

from __future__ import annotations

import pytest

from tests.evals.fixtures.triage_selection import (
    OUTCOMES,
    VERDICTS,
    LabelledPaper,
    LabelSet,
    build_report,
    labels_available,
    load_labels,
)


def _paper(idx: int, outcome: str, verdict: str, score: int = 50) -> LabelledPaper:
    return LabelledPaper(
        id=f"p{idx:03d}",
        arxiv_id=f"2610.{idx:05d}",
        outcome=outcome,  # type: ignore[arg-type]
        keep=outcome != "rejected",
        rough_implementability=score,
        verdict=verdict,  # type: ignore[arg-type]
    )


def _set(spec: dict[str, list[str]], populations: dict[str, int]) -> LabelSet:
    """`spec` maps an outcome to the verdicts of its sampled papers."""
    rows: list[LabelledPaper] = []
    i = 0
    for outcome, verdicts in spec.items():
        for v in verdicts:
            rows.append(_paper(i, outcome, v))
            i += 1
    return LabelSet(rows=tuple(rows), populations=populations, meta={})


@pytest.mark.unit
class TestSelectionMetrics:
    def test_base_rate_is_population_weighted_not_sample_weighted(self):
        """The whole point of recording populations.

        Equal sample sizes, but `capped` outnumbers `rejected` 10:1 in the pool. All the
        positives sit in `capped`, so the pool base rate must land near its rate, not near
        the unweighted mean of the three strata.
        """
        labels = _set(
            {
                "rejected": ["no"] * 10,
                "survived": ["no"] * 10,
                "capped": ["yes"] * 10,
            },
            populations={"rejected": 10, "survived": 10, "capped": 200},
        )
        report = build_report(labels, strict=True)
        # Unweighted this would be 1/3. Weighted: 200 positives of 220 papers.
        assert report.base_rate == pytest.approx(200 / 220, abs=1e-6)
        assert report.rates["capped"] == pytest.approx(1.0)

    def test_lift_is_zero_when_every_stratum_looks_the_same(self):
        """If selection carries no signal, the feed is no richer than the pool."""
        labels = _set(
            {
                "rejected": ["yes", "no"] * 5,
                "survived": ["yes", "no"] * 5,
                "capped": ["yes", "no"] * 5,
            },
            populations={"rejected": 140, "survived": 400, "capped": 1050},
        )
        report = build_report(labels, strict=True)
        assert report.base_rate == pytest.approx(0.5)
        assert report.precision_at_cap == pytest.approx(0.5)
        assert report.lift == pytest.approx(0.0)
        assert report.sort_key_separation == pytest.approx(0.0)

    def test_lift_is_positive_when_the_feed_is_richer_than_the_pool(self):
        labels = _set(
            {
                "rejected": ["no"] * 10,
                "survived": ["yes"] * 8 + ["no"] * 2,
                "capped": ["yes"] * 2 + ["no"] * 8,
            },
            populations={"rejected": 140, "survived": 400, "capped": 1050},
        )
        report = build_report(labels, strict=True)
        assert report.precision_at_cap == pytest.approx(0.8)
        assert report.lift > 0.4
        # Isolates the sort key from triage: 80% above the cut against 20% below it.
        assert report.sort_key_separation == pytest.approx(0.6)

    def test_sort_key_separation_goes_negative_when_the_key_is_backwards(self):
        """A sort key that ranks the wrong way must not be flattered to zero."""
        labels = _set(
            {
                "rejected": ["no"] * 5,
                "survived": ["no"] * 10,
                "capped": ["yes"] * 10,
            },
            populations={"rejected": 140, "survived": 400, "capped": 1050},
        )
        report = build_report(labels, strict=True)
        assert report.sort_key_separation == pytest.approx(-1.0)
        assert report.lift < 0

    def test_strict_and_loose_readings_differ_on_maybe(self):
        labels = _set(
            {
                "rejected": ["no"] * 5,
                "survived": ["maybe"] * 10,
                "capped": ["no"] * 10,
            },
            populations={"rejected": 140, "survived": 400, "capped": 1050},
        )
        strict = build_report(labels, strict=True)
        loose = build_report(labels, strict=False)
        assert strict.precision_at_cap == pytest.approx(0.0)
        assert loose.precision_at_cap == pytest.approx(1.0)

    def test_recall_is_one_when_triage_rejected_nothing_worth_keeping(self):
        labels = _set(
            {
                "rejected": ["no"] * 10,
                "survived": ["yes"] * 10,
                "capped": ["yes"] * 10,
            },
            populations={"rejected": 140, "survived": 400, "capped": 1050},
        )
        report = build_report(labels, strict=True)
        assert report.triage_recall == pytest.approx(1.0)
        assert report.triage_precision == pytest.approx(1.0)

    def test_recall_falls_when_triage_rejects_good_papers(self):
        """The failure mode a recall-biased prompt exists to avoid."""
        labels = _set(
            {
                "rejected": ["yes"] * 10,
                "survived": ["yes"] * 10,
                "capped": ["no"] * 10,
            },
            populations={"rejected": 100, "survived": 100, "capped": 100},
        )
        report = build_report(labels, strict=True)
        # 100 of 200 pool positives were thrown out before Stage 2 ever saw them.
        assert report.triage_recall == pytest.approx(0.5)

    def test_spearman_tracks_a_monotone_sort_key(self):
        rows = tuple(
            _paper(i, "capped", v, score=s)
            for i, (v, s) in enumerate(
                [("no", 10), ("no", 20), ("maybe", 40), ("maybe", 50), ("yes", 80), ("yes", 90)]
            )
        )
        labels = LabelSet(rows=rows, populations={"capped": 6}, meta={})
        assert build_report(labels, strict=True).spearman > 0.9

    def test_metrics_do_not_divide_by_zero_on_an_empty_stratum(self):
        labels = _set(
            {"rejected": [], "survived": ["yes"] * 5, "capped": ["no"] * 5},
            populations={"rejected": 0, "survived": 400, "capped": 1050},
        )
        report = build_report(labels, strict=True)
        assert report.rates["rejected"] == 0.0
        assert report.triage_recall == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.skipif(
    not labels_available(), reason="no labels yet; see scripts/sample_triage_labels"
)
class TestTriageSelectionLabels:
    def test_ids_and_arxiv_ids_are_unique(self):
        rows = load_labels().rows
        assert len({r.id for r in rows}) == len(rows)
        assert len({r.arxiv_id for r in rows}) == len(rows)

    def test_every_verdict_and_outcome_is_valid(self):
        for r in load_labels().rows:
            assert r.verdict in VERDICTS
            assert r.outcome in OUTCOMES

    def test_every_stratum_is_represented(self):
        """A missing stratum silently removes a term from the weighting."""
        labels = load_labels()
        for outcome in OUTCOMES:
            assert labels.of(outcome), f"stratum {outcome!r} has no labelled papers"

    def test_populations_are_present_and_at_least_the_sample(self):
        labels = load_labels()
        for outcome in OUTCOMES:
            population = labels.populations.get(outcome)
            assert population is not None, f"no population recorded for {outcome!r}"
            assert population >= len(labels.of(outcome))

    def test_keep_agrees_with_outcome(self):
        """`rejected` means triage said drop; the other two mean it said keep."""
        for r in load_labels().rows:
            assert r.keep == (r.outcome != "rejected")

    def test_verdicts_are_not_all_the_same(self):
        """An all-yes or all-no sheet makes every rate degenerate and the eval meaningless."""
        verdicts = {r.verdict for r in load_labels().rows}
        assert len(verdicts) > 1, f"every paper was labelled {verdicts}"


@pytest.mark.unit
@pytest.mark.skipif(
    not labels_available(), reason="no labels yet; see scripts/sample_triage_labels"
)
class TestSelectionReport:
    def test_report(self):
        """Prints both readings. Not gated yet -- see this module's docstring."""
        labels = load_labels()
        print()
        print(f"[triage-selection] {len(labels.rows)} labelled; pool {labels.populations}")
        for strict in (True, False):
            for line in build_report(labels, strict=strict).lines():
                print(line)
        assert len(labels.rows) >= 30, "too few labels to read anything into"
