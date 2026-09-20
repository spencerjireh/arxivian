"""Integration test: the Stage 2 scoring graph persists real paper_scores + evidence.

Uses the real test DB and real PaperRepository/ScoringRepository. The network-bound deps
(ingest, per-paper retrieval, the Jev judgments, Semantic Scholar) are mocked so the test is
hermetic -- real-Jev golden-set agreement is the eval gate, not here. Proves: a survivor
arxiv_id runs the graph end-to-end into a scored v2 row (derived columns + JSONB
dimensions/attributes), and a re-run upserts (no duplicate).
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

from src.clients.semantic_scholar_client import CitationMetrics
from src.clients.typesafe_client import ChoiceResult, ScoreResult, SystemOneResult
from src.models.paper_score import PaperScore, ScoreEvidence
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.services.scoring_service import questions as q
from src.services.scoring_service.context import ScoringContext
from src.services.scoring_service.scoring_graph_builder import build_scoring_graph
from src.services.scoring_service.state import RUBRIC_VERSION, DimensionScore, PaperAttributes


async def _fake_ask(state, questions, *, request_name) -> SystemOneResult:
    """Dispatch on the question keys, the way one Jev request answers many questions."""
    nouls: dict[str, float] = {}
    choices: dict[str, ChoiceResult] = {}
    scores: dict[str, ScoreResult] = {}
    for key in questions:
        if key in q.METHOD_CLARITY_CRITERIA:
            nouls[key] = 0.8  # expected 3.2 -> derived 80
        elif key in q.FEASIBILITY_AUX_QUESTIONS or key == "code_released":
            nouls[key] = 0.9
        elif key == "compute_tier":
            scores[key] = ScoreResult(
                score=3.2,
                probabilities={0: 0.0, 1: 0.0, 2: 0.2, 3: 0.4, 4: 0.4},
                confidence=0.4,
                legend=list(q.COMPUTE_TIER_LEVELS),
            )
        elif key == "data_access":
            choices[key] = ChoiceResult(
                choice="public benchmark or standard dataset",
                probabilities={"public benchmark or standard dataset": 0.9, "not stated": 0.1},
                confidence=0.9,
            )
        elif key == "task_type":
            choices[key] = ChoiceResult(
                choice="image classification",
                probabilities={"image classification": 1.0},
                confidence=1.0,
            )
        elif key == "model_family":
            choices[key] = ChoiceResult(
                choice="convolutional network",
                probabilities={"convolutional network": 1.0},
                confidence=1.0,
            )
    return SystemOneResult(
        nouls=nouls, choices=choices, scores=scores, model="jev-1.13.0", input_tokens=500
    )


def _context(db_session, paper) -> ScoringContext:
    """Real repos on the test session; network-bound deps mocked."""
    ingest_service = Mock()
    ingest_service.ingest_by_ids = AsyncMock()  # paper already seeded -> no-op

    search_service = Mock()
    search_service.retrieve_within_paper = AsyncMock(
        return_value=[Mock(chunk_text="We evaluate on the public ImageNet benchmark.")]
    )

    typesafe_client = Mock()
    typesafe_client.ask = AsyncMock(side_effect=_fake_ask)

    s2_client = Mock()
    s2_client.get_citation_metrics = AsyncMock(
        return_value=CitationMetrics(
            arxiv_id=paper.arxiv_id,
            found=True,
            citation_count=500,
            citations_per_month=12.0,
            demand_band="HIGH",
        )
    )

    return ScoringContext(
        typesafe_client=typesafe_client,
        semantic_scholar_client=s2_client,
        ingest_service=ingest_service,
        search_service=search_service,
        paper_repository=PaperRepository(db_session),
        scoring_repository=ScoringRepository(db_session),
        db_session=db_session,
        rubric_version=RUBRIC_VERSION,
    )


@pytest.mark.asyncio
async def test_scoring_graph_persists_scores_and_evidence(db_session, sample_processed_paper_data):
    paper = await PaperRepository(db_session).create(sample_processed_paper_data)
    graph = build_scoring_graph()
    config = {"configurable": {"context": _context(db_session, paper)}}

    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": RUBRIC_VERSION}, config)

    score = (
        await db_session.execute(select(PaperScore).where(PaperScore.paper_id == paper.id))
    ).scalar_one()
    assert score.rubric_version == RUBRIC_VERSION
    assert score.method_clarity_score == 80  # 4 x P(yes)=0.8 -> expected 3.2
    assert score.resource_feasibility_score == 80  # compute tier expected 3.2
    assert score.data_availability_score == 100  # public data -> gate PASS
    assert score.demand_score == 85  # HIGH band
    assert score.model == "jev-1.13.0"
    assert score.input_tokens == 1500  # 3 Jev requests x 500
    assert score.details is None

    # v2 source of truth round-trips through JSONB
    method = DimensionScore.from_jsonb(score.dimensions["method_clarity"])
    assert method.max_level == 4 and method.expected == 3.2
    assert [j.key for j in method.judgments] == list(q.METHOD_CLARITY_CRITERIA)
    gate = DimensionScore.from_jsonb(score.dimensions["data_availability"])
    assert gate.level == 1 and gate.probabilities[1] == 1.0
    attrs = PaperAttributes.model_validate(score.attributes)
    assert attrs.code_released.answer is True
    assert attrs.model_family.answer == "convolutional network"

    evidence = (
        (
            await db_session.execute(
                select(ScoreEvidence).where(ScoreEvidence.paper_score_id == score.id)
            )
        )
        .scalars()
        .all()
    )
    kinds = {e.kind for e in evidence}
    assert "citation" in kinds  # demand evidence
    assert "dataset" in kinds  # data-availability evidence


@pytest.mark.asyncio
async def test_rescore_upserts_no_duplicate(db_session, sample_processed_paper_data):
    paper = await PaperRepository(db_session).create(sample_processed_paper_data)
    graph = build_scoring_graph()
    config = {"configurable": {"context": _context(db_session, paper)}}

    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": RUBRIC_VERSION}, config)
    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": RUBRIC_VERSION}, config)

    rows = (
        (await db_session.execute(select(PaperScore).where(PaperScore.paper_id == paper.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1  # upsert, not duplicate
