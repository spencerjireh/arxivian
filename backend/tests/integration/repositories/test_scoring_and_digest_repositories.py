"""Integration tests for the feed read methods on ScoringRepository and DigestRepository."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.services.scoring_service.state import RUBRIC_VERSION


async def _scored(db_session, sample_paper_data, arxiv_id, *, evidence=()):
    paper = await PaperRepository(db_session).create({**sample_paper_data, "arxiv_id": arxiv_id})
    await ScoringRepository(db_session).upsert_score(
        paper_id=str(paper.id),
        rubric_version=RUBRIC_VERSION,
        scores={
            "method_clarity_score": 80,
            "resource_feasibility_score": 80,
            "data_availability_score": 100,
            "demand_score": 85,
        },
        dimensions={},
        evidence=list(evidence),
    )
    return paper


@pytest.mark.asyncio
async def test_get_by_paper_ids_and_by_id(db_session, sample_paper_data):
    a = await _scored(db_session, sample_paper_data, "r-a")
    b = await _scored(
        db_session,
        sample_paper_data,
        "r-b",
        evidence=[
            {
                "dimension": "code_released",
                "kind": "code",
                "text": "github.com/x",
                "source": "raw_text",
            }
        ],
    )
    repo = ScoringRepository(db_session)

    batch = await repo.get_by_paper_ids([a.id, b.id, uuid.uuid4()], RUBRIC_VERSION)
    assert set(batch) == {a.id, b.id}
    assert await repo.get_by_paper_ids([], RUBRIC_VERSION) == {}
    assert await repo.get_by_paper_ids([a.id], "v1") == {}

    with_evidence = await repo.get_by_paper_id(b.id, RUBRIC_VERSION, with_evidence=True)
    assert with_evidence is not None
    assert [e.dimension for e in with_evidence.evidence] == ["code_released"]
    assert await repo.get_by_paper_id(uuid.uuid4(), RUBRIC_VERSION) is None


@pytest.mark.asyncio
async def test_get_by_ids(db_session, sample_paper_data):
    a = await _scored(db_session, sample_paper_data, "p-a")
    repo = PaperRepository(db_session)
    assert [p.id for p in await repo.get_by_ids([a.id, uuid.uuid4()])] == [a.id]
    assert await repo.get_by_ids([]) == []


@pytest.mark.asyncio
async def test_list_weeks(db_session):
    repo = DigestRepository(db_session)
    entry = {"paper_id": str(uuid.uuid4()), "arxiv_id": "x", "title": "t"}
    await repo.upsert_digest(
        week_start=date(2026, 8, 3),
        category_key="cs.LG",
        categories=["cs.LG"],
        ranking=[entry, entry],
    )
    await repo.upsert_digest(
        week_start=date(2026, 8, 10), category_key="cs.LG", categories=["cs.LG"], ranking=[entry]
    )
    await repo.upsert_digest(
        week_start=date(2026, 8, 10), category_key="cs.CV", categories=["cs.CV"], ranking=[]
    )

    assert await repo.list_weeks("cs.LG") == [(date(2026, 8, 10), 1), (date(2026, 8, 3), 2)]
    assert await repo.list_weeks("cs.CV") == [(date(2026, 8, 10), 0)]
    assert await repo.list_weeks("nope") == []


@pytest.mark.asyncio
async def test_list_missing_demand_and_set_demand(db_session, sample_paper_data):
    repo = ScoringRepository(db_session)
    paper = await PaperRepository(db_session).create({**sample_paper_data, "arxiv_id": "d-null"})
    await repo.upsert_score(
        paper_id=str(paper.id),
        rubric_version=RUBRIC_VERSION,
        scores={
            "method_clarity_score": 80,
            "resource_feasibility_score": 80,
            "data_availability_score": 100,
            "demand_score": None,
        },
        dimensions={"method_clarity": {"dimension": "method_clarity"}},
        evidence=[
            {"dimension": "method_clarity", "kind": "pseudocode", "text": "x", "source": "s"}
        ],
    )
    await _scored(db_session, sample_paper_data, "d-full")

    missing = await repo.list_missing_demand(rubric_version=RUBRIC_VERSION, limit=10)
    assert [p.arxiv_id for _, p in missing] == ["d-null"]

    score, _ = missing[0]
    score = await repo.get_by_paper_id(score.paper_id, RUBRIC_VERSION, with_evidence=True)
    assert score is not None
    await repo.set_demand(
        score,
        demand_score=55,
        dimension={"dimension": "demand", "level": 1},
        evidence=[{"dimension": "demand", "kind": "citation", "text": "3/mo", "source": "S2"}],
    )

    reloaded = await repo.get_by_paper_id(score.paper_id, RUBRIC_VERSION, with_evidence=True)
    assert reloaded is not None
    assert reloaded.demand_score == 55
    assert reloaded.dimensions == {
        "method_clarity": {"dimension": "method_clarity"},
        "demand": {"dimension": "demand", "level": 1},
    }
    assert sorted(e.dimension for e in reloaded.evidence) == ["demand", "method_clarity"]
    assert await repo.list_missing_demand(rubric_version=RUBRIC_VERSION, limit=10) == []
