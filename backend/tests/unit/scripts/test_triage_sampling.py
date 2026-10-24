"""Logic checks on the triage dump and sampling scripts (no network, no LLM).

These two functions decide which stratum every paper lands in and which papers a human is
asked to judge. A bug in either silently mislabels the sample, and every number the
selection eval later reports inherits that error without any sign of it, so they are worth
pinning down even though `scripts/` sits outside the coverage gate.
"""

from types import SimpleNamespace

import pytest

from scripts.dump_triage_candidates import _rows
from scripts.sample_triage_labels import _sample


def _verdict(keep: bool, score: int) -> SimpleNamespace:
    return SimpleNamespace(
        keep=keep, rough_implementability=score, paper_class="method", reasoning="r"
    )


def _candidates(n: int) -> dict[str, dict[str, str]]:
    return {
        f"26{i:02d}.00001": {
            "arxiv_id": f"26{i:02d}.00001",
            "title": f"T{i}",
            "abstract": f"A{i}",
            "category": "cs.LG",
        }
        for i in range(n)
    }


@pytest.mark.unit
class TestRows:
    def test_outcomes_split_by_keep_and_cap(self):
        candidates = _candidates(5)
        ids = list(candidates)
        verdicts = {
            ids[0]: _verdict(True, 90),
            ids[1]: _verdict(True, 80),
            ids[2]: _verdict(True, 10),
            ids[3]: _verdict(False, 70),
            # ids[4] deliberately absent: the model omits ids from a batch response.
        }
        by_id = {r["arxiv_id"]: r for r in _rows(candidates, verdicts, cap=2)}

        assert by_id[ids[0]]["outcome"] == "survived"
        assert by_id[ids[1]]["outcome"] == "survived"
        # Kept, but below the cut -- this is the group the feed never shows.
        assert by_id[ids[2]]["outcome"] == "capped"
        # A high sort score must not rescue a rejected paper; `keep` is checked first.
        assert by_id[ids[3]]["outcome"] == "rejected"
        assert by_id[ids[4]]["outcome"] == "no_verdict"

    def test_cap_takes_the_highest_scores(self):
        candidates = _candidates(4)
        ids = list(candidates)
        verdicts = {
            i: _verdict(True, score) for i, score in zip(ids, [10, 99, 50, 70], strict=True)
        }
        survived = {
            r["arxiv_id"] for r in _rows(candidates, verdicts, cap=2) if r["outcome"] == "survived"
        }
        assert survived == {ids[1], ids[3]}

    def test_every_candidate_appears_exactly_once(self):
        candidates = _candidates(6)
        verdicts = {i: _verdict(True, 50) for i in list(candidates)[:3]}
        rows = _rows(candidates, verdicts, cap=1)
        assert len(rows) == 6
        assert len({r["arxiv_id"] for r in rows}) == 6

    def test_no_verdict_rows_carry_null_fields_not_defaults(self):
        """A missing verdict must not look like a real one scored zero."""
        candidates = _candidates(1)
        row = _rows(candidates, {}, cap=10)[0]
        assert row["keep"] is None
        assert row["rough_implementability"] is None
        assert row["paper_class"] is None


@pytest.mark.unit
class TestSample:
    def _rows_for(self, counts: dict[str, int]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for outcome, n in counts.items():
            out.extend({"arxiv_id": f"{outcome}-{i}", "outcome": outcome} for i in range(n))
        return out

    def test_takes_requested_size_per_stratum_and_reports_population(self):
        rows = self._rows_for({"rejected": 100, "survived": 100, "capped": 100})
        picked, populations = _sample(rows, {"rejected": 5, "survived": 7, "capped": 9}, seed=1)
        counts = {
            s: sum(1 for r in picked if r["outcome"] == s)
            for s in ("rejected", "survived", "capped")
        }
        assert counts == {"rejected": 5, "survived": 7, "capped": 9}
        assert populations == {"rejected": 100, "survived": 100, "capped": 100}

    def test_small_stratum_is_taken_whole_not_padded(self):
        rows = self._rows_for({"rejected": 3, "survived": 50, "capped": 50})
        picked, populations = _sample(rows, {"rejected": 40, "survived": 5, "capped": 5}, seed=1)
        assert sum(1 for r in picked if r["outcome"] == "rejected") == 3
        # The population, not the sample size, is what lets the eval reweight.
        assert populations["rejected"] == 3

    def test_empty_stratum_is_skipped_without_raising(self):
        rows = self._rows_for({"survived": 10, "capped": 10})
        picked, populations = _sample(rows, {"rejected": 5, "survived": 5, "capped": 5}, seed=1)
        assert populations["rejected"] == 0
        assert len(picked) == 10

    def test_same_seed_reproduces_the_sample(self):
        rows = self._rows_for({"rejected": 50, "survived": 50, "capped": 50})
        sizes = {"rejected": 10, "survived": 10, "capped": 10}
        first, _ = _sample(rows, sizes, seed=7)
        second, _ = _sample(rows, sizes, seed=7)
        other, _ = _sample(rows, sizes, seed=8)
        assert [r["arxiv_id"] for r in first] == [r["arxiv_id"] for r in second]
        assert [r["arxiv_id"] for r in first] != [r["arxiv_id"] for r in other]
