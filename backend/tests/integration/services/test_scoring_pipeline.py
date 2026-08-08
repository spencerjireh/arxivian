"""Integration test: the Stage 2 scoring graph persists real paper_scores + evidence.

Uses the real test DB and real PaperRepository/ScoringRepository. The network-bound deps
(ingest, per-paper retrieval, the LLM judges, Semantic Scholar) are mocked so the test is
hermetic -- real-LLM golden-set agreement is SPE-272, not here. Proves: a survivor arxiv_id
runs the graph end-to-end into a scored row, and a re-run upserts (no duplicate).
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

from src.clients.semantic_scholar_client import CitationMetrics
from src.models.paper_score import PaperScore, ScoreEvidence
from src.repositories.paper_repository import PaperRepository
from src.repositories.scoring_repository import ScoringRepository
from src.schemas.scoring_state import DimensionScore
from src.services.scoring_service.context import ScoringContext
from src.services.scoring_service.scoring_graph_builder import build_scoring_graph


def _context(db_session, paper) -> ScoringContext:
    """Real repos on the test session; network-bound deps mocked."""
    ingest_service = Mock()
    ingest_service.ingest_by_ids = AsyncMock()  # paper already seeded -> no-op

    search_service = Mock()
    search_service.retrieve_within_paper = AsyncMock(
        return_value=[Mock(chunk_text="We evaluate on the public ImageNet benchmark.")]
    )

    llm_client = Mock()
    llm_client.generate_structured = AsyncMock(
        return_value=DimensionScore(
            dimension="method_clarity", score=80, reasoning="clear pseudocode"
        )
    )

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
        llm_client=llm_client,
        semantic_scholar_client=s2_client,
        ingest_service=ingest_service,
        search_service=search_service,
        paper_repository=PaperRepository(db_session),
        scoring_repository=ScoringRepository(db_session),
        db_session=db_session,
        strong_model="openai/gpt-5-nano",
        rubric_version="v1",
    )


@pytest.mark.asyncio
async def test_scoring_graph_persists_scores_and_evidence(db_session, sample_processed_paper_data):
    paper = await PaperRepository(db_session).create(sample_processed_paper_data)
    graph = build_scoring_graph()
    config = {"configurable": {"context": _context(db_session, paper)}}

    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": "v1"}, config)

    score = (
        await db_session.execute(select(PaperScore).where(PaperScore.paper_id == paper.id))
    ).scalar_one()
    assert score.method_clarity_score == 80
    assert score.resource_feasibility_score == 80  # same mocked judge
    assert score.data_availability_score == 100  # public data -> gate PASS
    assert score.demand_score == 85  # HIGH band

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

    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": "v1"}, config)
    await graph.ainvoke({"arxiv_id": paper.arxiv_id, "rubric_version": "v1"}, config)

    rows = (
        (await db_session.execute(select(PaperScore).where(PaperScore.paper_id == paper.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1  # upsert, not duplicate
