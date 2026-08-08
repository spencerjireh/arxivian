"""Unit tests for the Stage 2 scoring-graph nodes."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.clients.semantic_scholar_client import CitationMetrics
from src.exceptions import ScoringError
from src.schemas.scoring_state import DimensionScore
from src.services.scoring_service.nodes.compose import compose_and_persist_node
from src.services.scoring_service.nodes.dimensions import (
    DEMAND_BAND_TO_SCORE,
    classify_data_gate,
    score_data_availability_node,
    score_demand_node,
    score_method_clarity_node,
    score_resource_feasibility_node,
)
from src.services.scoring_service.nodes.fetch_and_extract import (
    DIMENSION_PROBES,
    fetch_and_extract_node,
)


@pytest.fixture
def context():
    ctx = Mock()
    ctx.llm_client = Mock()
    ctx.llm_client.generate_structured = AsyncMock()
    ctx.semantic_scholar_client = Mock()
    ctx.semantic_scholar_client.get_citation_metrics = AsyncMock()
    ctx.ingest_service = Mock()
    ctx.ingest_service.ingest_by_ids = AsyncMock()
    ctx.search_service = Mock()
    ctx.search_service.retrieve_within_paper = AsyncMock()
    ctx.paper_repository = Mock()
    ctx.paper_repository.get_by_arxiv_id = AsyncMock()
    ctx.scoring_repository = Mock()
    ctx.scoring_repository.upsert_score = AsyncMock()
    ctx.strong_model = "openai/gpt-5-nano"
    ctx.rubric_version = "v1"
    return ctx


@pytest.fixture
def make_config(context):
    return {"configurable": {"context": context}}


def _base_state(**overrides):
    state = {
        "arxiv_id": "2106.09685",
        "paper_id": "11111111-1111-1111-1111-111111111111",
        "rubric_version": "v1",
        "paper_meta": {"title": "LoRA", "arxiv_id": "2106.09685", "abstract": "We propose..."},
        "extracted_spans": {"pseudocode": ["algo"], "compute": ["1x A100"], "dataset": ["GLUE"]},
    }
    state.update(overrides)
    return state


# --- classify_data_gate -----------------------------------------------------------------


class TestClassifyDataGate:
    def test_default_pass_when_no_signal(self):
        assert classify_data_gate(["ImageNet", "public benchmark"]) == (100, None)

    def test_default_pass_when_empty(self):
        assert classify_data_gate([]) == (100, None)

    def test_fail_on_proprietary_signal(self):
        score, matched = classify_data_gate(["a proprietary clinical dataset of patient scans"])
        assert score == 0
        assert matched in {"proprietary", "clinical", "patient"}


# --- data availability node -------------------------------------------------------------


class TestDataAvailabilityNode:
    @pytest.mark.asyncio
    async def test_pass_default(self, make_config):
        result = await score_data_availability_node(_base_state(), make_config)
        dim = result["data_availability_result"]
        assert dim.score == 100
        assert dim.dimension == "data_availability"

    @pytest.mark.asyncio
    async def test_fail_on_proprietary(self, make_config):
        state = _base_state(
            extracted_spans={"dataset": ["trained on a private in-house clinical dataset"]}
        )
        result = await score_data_availability_node(state, make_config)
        dim = result["data_availability_result"]
        assert dim.score == 0
        assert dim.evidence  # the dataset span is carried as evidence
        assert dim.evidence[0].kind == "dataset"


# --- demand node ------------------------------------------------------------------------


class TestDemandNode:
    @pytest.mark.parametrize("band,expected", [("HIGH", 85), ("MED", 55), ("LOW", 20)])
    @pytest.mark.asyncio
    async def test_band_to_score(self, context, make_config, band, expected):
        context.semantic_scholar_client.get_citation_metrics.return_value = CitationMetrics(
            arxiv_id="2106.09685",
            found=True,
            citation_count=100,
            citations_per_month=4.0,
            demand_band=band,
        )
        result = await score_demand_node(_base_state(), make_config)
        dim = result["demand_result"]
        assert dim.score == expected
        assert dim.evidence[0].kind == "citation"
        assert DEMAND_BAND_TO_SCORE[band] == expected

    @pytest.mark.asyncio
    async def test_soft_fail_on_s2_error(self, context, make_config):
        context.semantic_scholar_client.get_citation_metrics.side_effect = RuntimeError("s2 down")
        result = await score_demand_node(_base_state(), make_config)
        assert result["demand_result"] is None


# --- LLM judge nodes --------------------------------------------------------------------


class TestLLMDimensionNodes:
    @pytest.mark.asyncio
    async def test_method_clarity_happy(self, context, make_config):
        context.llm_client.generate_structured.return_value = DimensionScore(
            dimension="method_clarity", score=80, reasoning="clear pseudocode"
        )
        result = await score_method_clarity_node(_base_state(), make_config)
        assert result["method_clarity_result"].score == 80
        context.llm_client.generate_structured.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resource_feasibility_soft_fail(self, context, make_config):
        context.llm_client.generate_structured.side_effect = RuntimeError("llm timeout")
        result = await score_resource_feasibility_node(_base_state(), make_config)
        assert result["resource_feasibility_result"] is None


# --- fetch_and_extract node -------------------------------------------------------------


class TestFetchAndExtractNode:
    @pytest.mark.asyncio
    async def test_happy_builds_spans_and_meta(self, context, make_config):
        paper = Mock()
        paper.id = "22222222-2222-2222-2222-222222222222"
        paper.pdf_processed = True
        paper.title = "LoRA"
        paper.abstract = "We propose low-rank adaptation."
        context.paper_repository.get_by_arxiv_id.return_value = paper
        context.search_service.retrieve_within_paper.return_value = [
            Mock(chunk_text="some relevant chunk"),
        ]

        result = await fetch_and_extract_node({"arxiv_id": "2106.09685"}, make_config)

        context.ingest_service.ingest_by_ids.assert_awaited_once_with(["2106.09685"])
        # one retrieval per dimension probe
        assert context.search_service.retrieve_within_paper.await_count == len(DIMENSION_PROBES)
        assert set(result["extracted_spans"]) == set(DIMENSION_PROBES)
        assert result["paper_id"] == str(paper.id)
        assert result["paper_meta"]["title"] == "LoRA"

    @pytest.mark.asyncio
    async def test_hard_fail_when_paper_missing(self, context, make_config):
        context.paper_repository.get_by_arxiv_id.return_value = None
        with pytest.raises(ScoringError):
            await fetch_and_extract_node({"arxiv_id": "2106.09685"}, make_config)

    @pytest.mark.asyncio
    async def test_hard_fail_when_not_processed(self, context, make_config):
        paper = Mock()
        paper.pdf_processed = False
        context.paper_repository.get_by_arxiv_id.return_value = paper
        with pytest.raises(ScoringError):
            await fetch_and_extract_node({"arxiv_id": "2106.09685"}, make_config)


# --- compose_and_persist node -----------------------------------------------------------


class TestComposeNode:
    @pytest.mark.asyncio
    async def test_persists_scores_and_evidence(self, context, make_config):
        state = _base_state(
            method_clarity_result=DimensionScore(
                dimension="method_clarity",
                score=80,
                evidence=[],
                reasoning="clear",
            ),
            resource_feasibility_result=None,  # soft-failed
            data_availability_result=DimensionScore(
                dimension="data_availability", score=100, reasoning="public"
            ),
            demand_result=DimensionScore(dimension="demand", score=55, reasoning="steady"),
        )

        await compose_and_persist_node(state, make_config)

        context.scoring_repository.upsert_score.assert_awaited_once()
        kwargs = context.scoring_repository.upsert_score.call_args.kwargs
        assert kwargs["paper_id"] == state["paper_id"]
        assert kwargs["scores"]["method_clarity_score"] == 80
        assert kwargs["scores"]["resource_feasibility_score"] is None  # soft-failed -> null
        assert kwargs["scores"]["data_availability_score"] == 100
        assert kwargs["scores"]["demand_score"] == 55
        # failed dimension contributes no details entry
        assert "resource_feasibility" not in kwargs["details"]
        assert kwargs["details"]["method_clarity"]["model"] == "openai/gpt-5-nano"
