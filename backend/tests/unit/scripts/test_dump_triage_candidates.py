"""Logic checks on the triage dump script (no network, no LLM).

`_rows` decides which stratum every candidate lands in -- rejected, capped, survived -- which
is what makes a dump readable at all. Stage 1 persists nothing, so this script is the only
window into triage behaviour, and a bug here misreports the funnel silently rather than
failing. `scripts/` sits outside the coverage gate, so these are the only guard it has.
"""

from types import SimpleNamespace

import pytest

from scripts.dump_triage_candidates import _rows


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
