"""Human labels for the Stage 1 selection decision, and the metrics over them.

The feed is not selected by triage. Across the two unattended production runs triage
rejected 165 of 1633 and then 139 of 1591, so roughly 91% of candidates pass; what actually
chooses the feed is the `rough_implementability` sort (`scoring_service/triage.py`) and the
cut at `triage_max_survivors`. Nothing had ever checked either against a human, and Stage 1
persists nothing, so the sample behind these labels was generated fresh by
`scripts/dump_triage_candidates.py` and drawn by `scripts/sample_triage_labels.py`.

Labels were collected **blind**: the labeller saw only arXiv id, title and abstract, never
`keep` or `rough_implementability`. That is what makes the numbers below mean anything.

Three outcomes per paper, answering "would you spend a weekend implementing this":

    yes    worth building
    maybe  genuinely borderline
    no     not worth it

Two readings are reported rather than one, because forcing `maybe` to a side is a judgment
the data cannot make: **strict** counts only `yes`, **loose** counts `yes` or `maybe`.

## Why the weighting exists

The sample is stratified -- about 40 rejected, 50 survived, 60 capped -- because the strata
are wildly unequal in the pool (roughly 140 rejected against 1050 capped). Rejects are
therefore massively oversampled, and a rate read straight off the sample would be biased
toward whatever the rejects look like. Every pool-level figure here weights each stratum by
`population / sampled`, which is why `populations` is part of the fixture and not a comment.

## The number that matters

`lift` compares `precision_at_cap` -- the human-positive rate among the papers the feed
actually shows -- against the pool-wide base rate. If selection is informative, the feed is
richer in positives than the pool. If `lift` is around zero, the top-N-by-sort-key is no
better than drawing at random, and the cap is discarding ~1300 papers a week on the strength
of a number that carries no signal.

`sort_key_separation` isolates the sort key from triage: among papers triage kept, it is the
positive rate above the cut minus the rate below it. Triage's own contribution shows up in
`triage_precision` / `triage_recall` instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["yes", "maybe", "no"]
Outcome = Literal["rejected", "survived", "capped"]

VERDICTS: tuple[Verdict, ...] = ("yes", "maybe", "no")
# `no_verdict` is excluded on purpose: a paper the model omitted from a batch response is a
# reliability problem (measured separately as the no_verdict rate), not a selection decision.
OUTCOMES: tuple[Outcome, ...] = ("rejected", "survived", "capped")

LABELS_PATH = Path(__file__).parent / "triage_selection_labels.json"


@dataclass(frozen=True)
class LabelledPaper:
    """One blind-labelled candidate, joined back to the triage verdict it was hidden from."""

    id: str
    arxiv_id: str
    outcome: Outcome
    keep: bool
    rough_implementability: int
    verdict: Verdict


@dataclass(frozen=True)
class LabelSet:
    rows: tuple[LabelledPaper, ...]
    populations: dict[str, int]
    meta: dict[str, Any]

    def of(self, outcome: Outcome) -> tuple[LabelledPaper, ...]:
        return tuple(r for r in self.rows if r.outcome == outcome)

    def weight(self, outcome: Outcome) -> float:
        """Population per sampled paper, so a stratum counts for its true share."""
        sampled = len(self.of(outcome))
        if not sampled:
            return 0.0
        return self.populations.get(outcome, 0) / sampled


def labels_available() -> bool:
    return LABELS_PATH.exists()


def load_labels(path: Path | None = None) -> LabelSet:
    raw = json.loads((path or LABELS_PATH).read_text())
    rows = tuple(
        LabelledPaper(
            id=str(r["id"]),
            arxiv_id=str(r["arxiv_id"]),
            outcome=r["outcome"],
            keep=bool(r["keep"]),
            rough_implementability=int(r["rough_implementability"]),
            verdict=r["verdict"],
        )
        for r in raw["rows"]
        if r.get("verdict") in VERDICTS and r.get("outcome") in OUTCOMES
    )
    return LabelSet(
        rows=rows,
        populations={k: int(v) for k, v in raw["populations"].items()},
        meta={k: v for k, v in raw.items() if k not in {"rows", "populations"}},
    )


def _is_positive(verdict: Verdict, *, strict: bool) -> bool:
    return verdict == "yes" if strict else verdict in ("yes", "maybe")


def positive_rate(papers: tuple[LabelledPaper, ...], *, strict: bool) -> float:
    if not papers:
        return 0.0
    return sum(1 for p in papers if _is_positive(p.verdict, strict=strict)) / len(papers)


@dataclass(frozen=True)
class SelectionReport:
    strict: bool
    sampled: dict[str, int]
    rates: dict[str, float]
    base_rate: float
    precision_at_cap: float
    lift: float
    sort_key_separation: float
    triage_precision: float
    triage_recall: float
    spearman: float

    def lines(self) -> list[str]:
        reading = "strict (yes only)" if self.strict else "loose (yes or maybe)"
        out = [f"[triage-selection] {reading}"]
        for outcome in OUTCOMES:
            n = self.sampled.get(outcome, 0)
            out.append(f"  {outcome:<10} n={n:<4} positive={self.rates.get(outcome, 0.0):.1%}")
        out += [
            f"  pool base rate      {self.base_rate:.1%}  (population-weighted)",
            f"  precision@cap       {self.precision_at_cap:.1%}  (what the feed shows)",
            f"  LIFT                {self.lift:+.1%}  (feed minus pool; ~0 means no signal)",
            f"  sort-key separation {self.sort_key_separation:+.1%}  (above cut minus below)",
            f"  triage precision    {self.triage_precision:.1%}",
            f"  triage recall       {self.triage_recall:.1%}",
            f"  spearman(score,label) {self.spearman:+.3f}  (diagnostic)",
        ]
        return out


def _spearman(pairs: list[tuple[float, float]]) -> float:
    """Rank correlation with tie-averaged ranks. Returns 0.0 when undefined."""
    if len(pairs) < 3:
        return 0.0

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out

    rx = ranks([p[0] for p in pairs])
    ry = ranks([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def build_report(labels: LabelSet, *, strict: bool) -> SelectionReport:
    rates = {o: positive_rate(labels.of(o), strict=strict) for o in OUTCOMES}
    sampled = {o: len(labels.of(o)) for o in OUTCOMES}

    # Population-weighted positives and totals, so the oversampled rejects do not dominate.
    weighted_pos = {o: labels.populations.get(o, 0) * rates[o] for o in OUTCOMES}
    weighted_total = {o: float(labels.populations.get(o, 0)) for o in OUTCOMES}

    pool_total = sum(weighted_total.values())
    base_rate = sum(weighted_pos.values()) / pool_total if pool_total else 0.0

    kept_total = weighted_total["survived"] + weighted_total["capped"]
    kept_pos = weighted_pos["survived"] + weighted_pos["capped"]
    all_pos = sum(weighted_pos.values())

    label_value = {"no": 0.0, "maybe": 1.0, "yes": 2.0}
    spearman = _spearman(
        [(float(r.rough_implementability), label_value[r.verdict]) for r in labels.rows]
    )

    return SelectionReport(
        strict=strict,
        sampled=sampled,
        rates=rates,
        base_rate=base_rate,
        # The survived stratum IS the top-cap by sort key, so its rate is precision@cap.
        precision_at_cap=rates["survived"],
        lift=rates["survived"] - base_rate,
        sort_key_separation=rates["survived"] - rates["capped"],
        triage_precision=(kept_pos / kept_total) if kept_total else 0.0,
        triage_recall=(kept_pos / all_pos) if all_pos else 0.0,
        spearman=spearman,
    )
