"""Tests for FeedService.get_feed over mocked repositories."""

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.feed_service import FeedService

WEEK = date(2026, 8, 3)
KEY = "cs.AI,cs.LG"


def _dim(name, level, max_level, confidence=0.9, judgments=()):
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


def _paper(arxiv_id, categories=("cs.LG",), title="T", abstract="A"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        arxiv_id=arxiv_id,
        title=title,
        authors=["A"],
        abstract=abstract,
        categories=list(categories),
        published_date=datetime(2026, 8, 1, tzinfo=UTC),
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    )


def _score(paper, *, method=80, feasibility=80, demand=85, feas_level=3):
    return SimpleNamespace(
        paper_id=paper.id,
        method_clarity_score=method,
        resource_feasibility_score=feasibility,
        data_availability_score=100,
        demand_score=demand,
        dimensions={
            "method_clarity": _dim("method_clarity", 3, 4),
            "resource_feasibility": _dim("resource_feasibility", feas_level, 4),
            "data_availability": _dim("data_availability", 1, 1),
        },
        attributes=None,
        updated_at=datetime(2026, 8, 4, tzinfo=UTC),
    )


def _state(paper, state):
    return SimpleNamespace(
        paper_id=paper.id,
        state=state,
        repo_url=None,
        dismissal_reason=None,
        updated_at=datetime(2026, 8, 5, tzinfo=UTC),
    )


def _entry(paper, composite=80.0):
    return {
        "paper_id": str(paper.id),
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "method_clarity_score": 80,
        "resource_feasibility_score": 80,
        "data_availability_score": 100,
        "demand_score": 85,
        "provisional_composite": composite,
    }


def _user(preferences=None):
    return SimpleNamespace(id=uuid.uuid4(), preferences=preferences)


def _service(*, weeks, digest, papers, scores, states):
    digest_repo = AsyncMock()
    digest_repo.list_weeks = AsyncMock(return_value=weeks)
    digest_repo.get_by_week = AsyncMock(return_value=digest)
    scoring_repo = AsyncMock()
    scoring_repo.get_by_paper_ids = AsyncMock(return_value={s.paper_id: s for s in scores})
    paper_repo = AsyncMock()
    paper_repo.get_by_ids = AsyncMock(return_value=papers)
    state_repo = AsyncMock()
    state_repo.get_many = AsyncMock(return_value={s.paper_id: s for s in states})
    return FeedService(
        digest_repo=digest_repo,
        scoring_repo=scoring_repo,
        paper_repo=paper_repo,
        state_repo=state_repo,
        category_key=KEY,
    )


def _digest(entries, categories=("cs.AI", "cs.LG")):
    return SimpleNamespace(week_start=WEEK, categories=list(categories), ranking=entries)


@pytest.mark.unit
class TestGetFeed:
    async def test_no_digests(self):
        svc = _service(weeks=[], digest=None, papers=[], scores=[], states=[])
        out = await svc.get_feed(_user())
        assert out.week_start is None and out.items == [] and out.available_weeks == []

    async def test_missing_week_returns_empty_not_error(self):
        svc = _service(weeks=[(WEEK, 3)], digest=None, papers=[], scores=[], states=[])
        out = await svc.get_feed(_user(), week=date(2026, 7, 1))
        assert out.week_start == date(2026, 6, 29)
        assert out.total == 0 and len(out.available_weeks) == 1

    async def test_default_week_is_newest_and_snaps_explicit_week(self):
        p = _paper("1")
        svc = _service(
            weeks=[(WEEK, 1), (date(2026, 7, 27), 1)],
            digest=_digest([_entry(p)]),
            papers=[p],
            scores=[_score(p)],
            states=[],
        )
        out = await svc.get_feed(_user())
        assert out.week_start == WEEK
        svc.digest_repo.get_by_week.assert_awaited_with(WEEK, KEY)
        await svc.get_feed(_user(), week=date(2026, 8, 6))
        svc.digest_repo.get_by_week.assert_awaited_with(WEEK, KEY)

    async def test_orders_by_live_composite_not_snapshot(self):
        a, b = _paper("a"), _paper("b")
        svc = _service(
            weeks=[(WEEK, 2)],
            digest=_digest([_entry(a, composite=99.0), _entry(b, composite=10.0)]),
            papers=[a, b],
            scores=[_score(a, method=40, feasibility=40, demand=20), _score(b)],
            states=[],
        )
        out = await svc.get_feed(_user())
        assert [i.paper.arxiv_id for i in out.items] == ["b", "a"]
        assert out.items[0].scores.composite == 81.5

    async def test_filters_category_min_score_and_dismissed(self):
        a, b, c = _paper("a", ["cs.CV"]), _paper("b"), _paper("c")
        svc = _service(
            weeks=[(WEEK, 3)],
            digest=_digest([_entry(a), _entry(b), _entry(c)]),
            papers=[a, b, c],
            scores=[_score(a), _score(b, method=10, feasibility=10, demand=20), _score(c)],
            states=[_state(c, "dismissed")],
        )
        assert [i.paper.arxiv_id for i in (await svc.get_feed(_user())).items] == ["a", "b"]
        assert [
            i.paper.arxiv_id for i in (await svc.get_feed(_user(), categories=["cs.LG"])).items
        ] == ["b"]
        assert [i.paper.arxiv_id for i in (await svc.get_feed(_user(), min_score=40)).items] == [
            "a"
        ]
        with_dismissed = await svc.get_feed(_user(), include_dismissed=True)
        assert [i.paper.arxiv_id for i in with_dismissed.items] == ["a", "c", "b"]
        assert with_dismissed.items[1].state.state == "dismissed"

    async def test_pagination_total_is_post_filter(self):
        papers = [_paper(str(i)) for i in range(5)]
        svc = _service(
            weeks=[(WEEK, 5)],
            digest=_digest([_entry(p) for p in papers]),
            papers=papers,
            scores=[_score(p) for p in papers],
            states=[_state(papers[0], "dismissed")],
        )
        out = await svc.get_feed(_user(), offset=1, limit=2)
        assert out.total == 4 and len(out.items) == 2 and out.offset == 1 and out.limit == 2

    async def test_skips_entries_with_missing_rows(self):
        a, b = _paper("a"), _paper("b")
        svc = _service(
            weeks=[(WEEK, 2)],
            digest=_digest([_entry(a), _entry(b), {"garbage": True}]),
            papers=[a, b],
            scores=[_score(a)],
            states=[],
        )
        out = await svc.get_feed(_user())
        assert [i.paper.arxiv_id for i in out.items] == ["a"]

    async def test_compute_profile_ranks_matches_first(self):
        fits, big = _paper("fits"), _paper("big")
        svc = _service(
            weeks=[(WEEK, 2)],
            digest=_digest([_entry(fits), _entry(big)]),
            papers=[fits, big],
            scores=[
                _score(fits, method=50, feasibility=75, demand=20, feas_level=3),
                _score(big, method=100, feasibility=100, demand=85, feas_level=1),
            ],
            states=[],
        )
        user = _user({"feed_profile": {"categories": ["cs.LG"], "compute_profile": "laptop"}})
        out = await svc.get_feed(user)
        assert [i.paper.arxiv_id for i in out.items] == ["fits", "big"]
        assert out.items[0].signals.compute_match is True
        assert out.items[1].signals.compute_match is False
        no_profile = await svc.get_feed(_user())
        assert [i.paper.arxiv_id for i in no_profile.items] == ["big", "fits"]
        assert no_profile.items[0].signals.compute_match is None

    async def test_keyword_tie_break(self):
        kw, other = _paper("kw", title="Sparse attention"), _paper("other", title="Plain")
        svc = _service(
            weeks=[(WEEK, 2)],
            digest=_digest([_entry(kw), _entry(other)]),
            papers=[kw, other],
            scores=[_score(kw, method=50, feasibility=50, demand=55), _score(other)],
            states=[],
        )
        user = _user({"feed_profile": {"keywords": ["ATTENTION"]}})
        out = await svc.get_feed(user)
        assert [i.paper.arxiv_id for i in out.items] == ["kw", "other"]
        assert out.items[0].keyword_match is True

    async def test_categories_available_from_digest(self):
        p = _paper("1")
        svc = _service(
            weeks=[(WEEK, 1)],
            digest=_digest([_entry(p)]),
            papers=[p],
            scores=[_score(p)],
            states=[],
        )
        out = await svc.get_feed(_user())
        assert out.categories_available == ["cs.AI", "cs.LG"]


@pytest.mark.unit
class TestGetLibrary:
    def _service_for(self, rows, scores):
        svc = _service(weeks=[], digest=None, papers=[], scores=scores, states=[])
        svc.state_repo.list_for_user = AsyncMock(return_value=rows)
        return svc

    async def test_groups_by_state_and_keeps_order(self):
        a, b, c = _paper("a"), _paper("b"), _paper("c")
        rows = [(_state(c, "shipped"), c), (_state(b, "saved"), b), (_state(a, "saved"), a)]
        rows[0][0].repo_url = "https://github.com/x/y"
        svc = self._service_for(rows, [_score(a), _score(b), _score(c)])

        out = await svc.get_library(_user())

        assert [i.paper.arxiv_id for i in out.saved] == ["b", "a"]
        assert out.implementing == []
        assert out.shipped[0].state.repo_url == "https://github.com/x/y"
        assert out.saved[0].scores.composite > 0 and out.saved[0].verdict
        svc.scoring_repo.get_by_paper_ids.assert_awaited_once()
        assert set(svc.scoring_repo.get_by_paper_ids.await_args.args[0]) == {a.id, b.id, c.id}

    async def test_unscored_paper_keeps_its_card(self):
        a = _paper("a", title="Sparse attention")
        svc = self._service_for([(_state(a, "implementing"), a)], [])

        out = await svc.get_library(_user({"feed_profile": {"keywords": ["attention"]}}))

        card = out.implementing[0]
        assert card.scores is None and card.verdict is None and card.signals is None
        assert card.scored_at is None and card.low_confidence == []
        assert card.keyword_match is True
        assert card.state.state == "implementing"

    async def test_empty_library(self):
        svc = self._service_for([], [])
        out = await svc.get_library(_user())
        assert (out.saved, out.implementing, out.shipped) == ([], [], [])


def _evidence(dimension, kind, text):
    return SimpleNamespace(dimension=dimension, kind=kind, text=text, source="raw_text")


@pytest.mark.unit
class TestGetScoreDetail:
    def _service_for(self, paper, score, state=None):
        svc = _service(weeks=[], digest=None, papers=[], scores=[], states=[])
        svc.paper_repo.get_by_arxiv_id = AsyncMock(return_value=paper)
        svc.scoring_repo.get_by_paper_id = AsyncMock(return_value=score)
        svc.state_repo.get = AsyncMock(return_value=state)
        return svc

    async def test_none_when_missing_unprocessed_or_unscored(self):
        paper = _paper("x")
        paper.pdf_processed = True
        svc = self._service_for(None, None)
        assert await svc.get_score_detail(_user(), "x") is None

        unprocessed = _paper("x")
        unprocessed.pdf_processed = False
        svc = self._service_for(unprocessed, _score(unprocessed))
        assert await svc.get_score_detail(_user(), "x") is None

        svc = self._service_for(paper, None)
        assert await svc.get_score_detail(_user(), "x") is None
        svc.scoring_repo.get_by_paper_id.assert_awaited_once_with(
            paper.id, "v2", with_evidence=True
        )

    async def test_builds_ordered_breakdown_with_partitioned_evidence(self):
        paper = _paper("x")
        paper.pdf_processed = True
        score = _score(paper, feas_level=2)
        score.rubric_version = "v2"
        score.attributes = {
            "code_released": {
                "key": "code_released",
                "kind": "noul",
                "answer": True,
                "probabilities": {"yes": 0.9, "no": 0.1},
                "confidence": 0.9,
                "legend": None,
            }
        }
        score.evidence = [
            _evidence("resource_feasibility", "compute", "8 GPUs"),
            _evidence("method_clarity", "pseudocode", "Algorithm 1"),
            _evidence("code_released", "code", "github.com/x/y"),
        ]
        svc = self._service_for(paper, score, state=_state(paper, "saved"))

        out = await svc.get_score_detail(_user(), "x")
        assert out is not None
        assert [d.dimension for d in out.dimensions] == [
            "method_clarity",
            "resource_feasibility",
            "data_availability",
        ]
        assert out.dimensions[0].evidence[0].text == "Algorithm 1"
        assert out.dimensions[1].evidence[0].kind == "compute"
        assert out.dimensions[2].evidence == []
        assert out.dimensions[0].probabilities == {0: 0.0, 1: 0.0, 2: 0.0, 3: 1.0, 4: 0.0}
        assert out.dimensions[1].band == "MED" and out.dimensions[1].score == 50
        assert out.attributes.code_released is not None
        assert out.attributes.code_released.answer is True
        assert [e.text for e in out.attributes.code_evidence] == ["github.com/x/y"]
        assert out.signals.code_released is True
        assert out.state is not None and out.state.state == "saved"
        assert out.scores.composite == 81.5
