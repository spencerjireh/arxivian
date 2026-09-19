"""Integration test: FeedService.get_feed over a digest built by build_digest_for_week."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.repositories.digest_repository import DigestRepository
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository
from src.schemas.digest import category_key_for
from src.schemas.scoring_state import RUBRIC_VERSION
from src.services.feed_service import FeedService
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
    now = datetime.now(timezone.utc)
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
        category_key=category_key_for(categories),
    )

    page = await service.get_feed(created_user)
    assert [i.paper.arxiv_id for i in page.items] == ["f-top", "f-fits"]
    assert page.categories_available == sorted(categories) or set(page.categories_available) == set(
        categories
    )
    assert page.available_weeks[0].paper_count == 2
    first = page.items[0]
    assert (
        first.verdict
        == "Convolutional network for image classification; multi-GPU node; public data"
    )
    assert first.signals.model_dump() == {
        "pseudocode_present": True,
        "public_datasets": True,
        "single_gpu": False,
        "code_released": True,
        "compute_match": None,
    }
    assert first.scores.composite == 88.5

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
    assert page.items[0].signals.compute_match is True
    assert fits.id is not None
