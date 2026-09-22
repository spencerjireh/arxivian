"""Integration test: FeedService.get_feed over a digest built by build_digest_for_week."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.clients.arxiv_client import ArxivClient
from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.services.feed_service import FeedService
from src.services.feed_service.digest import category_key_for
from src.services.scoring_service.state import RUBRIC_VERSION
from src.tasks.digest_tasks import build_digest_for_week


def _dim(name, level, max_level, judgments=()):
    probs = {str(i): 0.0 for i in range(max_level + 1)}
    probs[str(level)] = 1.0
    return {
        "dimension": name,
        "level": level,
        "max_level": max_level,
        "expected": float(level),
        "probabilities": probs,
        "confidence": 0.9,
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


def _choice(key, answer):
    return {
        "key": key,
        "kind": "choice",
        "answer": answer,
        "probabilities": {answer: 0.9},
        "confidence": 0.9,
        "legend": None,
    }


async def _scored(db_session, sample_paper_data, arxiv_id, *, scores, feas_level, categories):
    paper = await PaperRepository(db_session).create(
        {**sample_paper_data, "arxiv_id": arxiv_id, "categories": categories, "pdf_processed": True}
    )
    method, feasibility, data, demand = scores
    await ScoringRepository(db_session).upsert_score(
        paper_id=str(paper.id),
        rubric_version=RUBRIC_VERSION,
        scores={
            "method_clarity_score": method,
            "resource_feasibility_score": feasibility,
            "data_availability_score": data,
            "demand_score": demand,
        },
        dimensions={
            "method_clarity": _dim("method_clarity", 3, 4, [_noul("algorithm_given", 0.9)]),
            "resource_feasibility": _dim("resource_feasibility", feas_level, 4),
            "data_availability": _dim(
                "data_availability",
                1,
                1,
                [_choice("data_access", "public benchmark or standard dataset")],
            ),
        },
        evidence=[],
        attributes={
            "code_released": _noul("code_released", 0.8),
            "task_type": _choice("task_type", "image classification"),
            "model_family": _choice("model_family", "convolutional network"),
        },
        model="jev-1.13.0",
        input_tokens=100,
    )
    return paper


@pytest.mark.asyncio
async def test_feed_end_to_end(db_session, sample_paper_data, created_user):
    now = datetime.now(UTC)
    categories = ["cs.LG", "cs.CV"]
    top = await _scored(
        db_session,
        sample_paper_data,
        "f-top",
        scores=(90, 90, 100, 85),
        feas_level=1,
        categories=["cs.LG"],
    )
    fits = await _scored(
        db_session,
        sample_paper_data,
        "f-fits",
        scores=(60, 75, 100, 55),
        feas_level=3,
        categories=["cs.CV"],
    )
    await build_digest_for_week(db_session, categories=categories, now=now)

    service = FeedService(
        digest_repo=DigestRepository(db_session),
        scoring_repo=ScoringRepository(db_session),
        paper_repo=PaperRepository(db_session),
        state_repo=UserPaperStateRepository(db_session),
        arxiv_client=ArxivClient(rate_limit_delay=0.0),
        category_key=category_key_for(categories),
    )

    page = await service.get_feed(created_user)
    assert [i.paper.arxiv_id for i in page.items] == ["f-top", "f-fits"]
    assert page.categories_available == sorted(categories) or set(page.categories_available) == set(
        categories
    )
    assert page.available_weeks[0].paper_count == 2
    first = page.items[0]
    assert first.headline == "Convolutional network for image classification"
    assert first.meta == ["multi-GPU node", "public data", "code released", "pseudocode given"]
    assert first.compute_match is None
    assert first.scores.composite == 88.5

    # anonymous: same cards, default order, no state
    anon = await service.get_feed(None)
    assert [i.paper.arxiv_id for i in anon.items] == ["f-top", "f-fits"]
    assert all(i.state is None and i.compute_match is None for i in anon.items)

    # category filter + dismissed exclusion
    await UserPaperStateRepository(db_session).upsert(
        user_id=created_user.id,
        paper_id=top.id,
        state="dismissed",
        repo_url=None,
        dismissal_reason=None,
    )
    page = await service.get_feed(created_user)
    assert [i.paper.arxiv_id for i in page.items] == ["f-fits"]
    page = await service.get_feed(created_user, include_dismissed=True, categories=["cs.LG"])
    assert [i.paper.arxiv_id for i in page.items] == ["f-top"]
    assert page.items[0].state is not None and page.items[0].state.state == "dismissed"

    # compute profile re-ranks the laptop-feasible paper first
    created_user.preferences = {
        "feed_profile": {"categories": ["cs.LG"], "compute_profile": "laptop"}
    }
    page = await service.get_feed(created_user, include_dismissed=True)
    assert [i.paper.arxiv_id for i in page.items] == ["f-fits", "f-top"]
    assert page.items[0].compute_match is True
    assert fits.id is not None


@pytest.mark.asyncio
async def test_score_detail_partitions_evidence(db_session, sample_paper_data, created_user):
    paper = await _scored(
        db_session,
        sample_paper_data,
        "f-detail",
        scores=(80, 50, 100, 55),
        feas_level=2,
        categories=["cs.LG"],
    )
    await ScoringRepository(db_session).upsert_score(
        paper_id=str(paper.id),
        rubric_version=RUBRIC_VERSION,
        scores={
            "method_clarity_score": 80,
            "resource_feasibility_score": 50,
            "data_availability_score": 100,
            "demand_score": 55,
        },
        dimensions={
            "method_clarity": _dim("method_clarity", 3, 4, [_noul("algorithm_given", 0.9)]),
            "resource_feasibility": _dim("resource_feasibility", 2, 4),
        },
        evidence=[
            {
                "dimension": "method_clarity",
                "kind": "pseudocode",
                "text": "Algorithm 1",
                "source": "s",
            },
            {
                "dimension": "code_released",
                "kind": "code",
                "text": "github.com/x",
                "source": "raw_text",
            },
        ],
        attributes={"code_released": _noul("code_released", 0.8)},
    )
    service = FeedService(
        digest_repo=DigestRepository(db_session),
        scoring_repo=ScoringRepository(db_session),
        paper_repo=PaperRepository(db_session),
        state_repo=UserPaperStateRepository(db_session),
        arxiv_client=ArxivClient(rate_limit_delay=0.0),
        category_key="cs.LG",
    )

    detail = await service.get_score_detail(created_user, "f-detail")
    assert detail is not None
    assert [d.dimension for d in detail.dimensions] == ["method_clarity", "resource_feasibility"]
    assert detail.dimensions[0].evidence[0].text == "Algorithm 1"
    assert detail.dimensions[1].evidence == []
    assert [e.text for e in detail.attributes.code_evidence] == ["github.com/x"]
    assert detail.dimensions[0].probabilities[3] == 1.0
    assert await service.get_score_detail(created_user, "nope") is None
