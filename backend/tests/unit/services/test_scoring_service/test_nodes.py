"""Unit tests for the Stage 2 scoring-graph nodes (rubric v2, Jev-backed)."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.clients.semantic_scholar_client import CitationMetrics
from src.clients.typesafe_client import ChoiceResult, ScoreResult, SystemOneResult
from src.exceptions import ScoringError, TypeSafeConnectionError, TypeSafeRateLimitError
from src.schemas.scoring_state import RUBRIC_VERSION, DimensionScore, EvidenceSpan
from src.services.scoring_service import questions as q
from src.services.scoring_service.judgments import demand_from_band
from src.services.scoring_service.nodes.compose import compose_and_persist_node
from src.services.scoring_service.nodes.dimensions import (
    DEMAND_BAND_TO_SCORE,
    score_data_availability_node,
    score_demand_node,
    score_method_clarity_node,
    score_resource_feasibility_node,
)
from src.services.scoring_service.nodes.fetch_and_extract import (
    DIMENSION_PROBES,
    fetch_and_extract_node,
)

PAPER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def context():
    ctx = Mock()
    ctx.typesafe_client = Mock()
    ctx.typesafe_client.ask = AsyncMock()
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
    ctx.db_session = Mock()
    ctx.db_session.commit = AsyncMock()
    ctx.rubric_version = RUBRIC_VERSION
    return ctx


@pytest.fixture
def make_config(context):
    return {"configurable": {"context": context}}


def _base_state(**overrides):
    state = {
        "arxiv_id": "2106.09685",
        "paper_id": PAPER_ID,
        "rubric_version": RUBRIC_VERSION,
        "paper_meta": {"title": "LoRA", "arxiv_id": "2106.09685", "abstract": "We propose..."},
        "extracted_spans": {
            "pseudocode": ["algo"],
            "compute": ["1x A100"],
            "dataset": ["GLUE"],
            "code_mentions": ["https://github.com/microsoft/LoRA"],
        },
        "sections": {
            "abstract": "We propose...",
            "method": "3 Method ...",
            "experiments": "4 Experiments ...",
            "appendix_headings": "",
        },
    }
    state.update(overrides)
    return state


def _result(
    *,
    nouls: dict[str, float] | None = None,
    choices: dict[str, ChoiceResult] | None = None,
    scores: dict[str, ScoreResult] | None = None,
    input_tokens: int = 1000,
) -> SystemOneResult:
    return SystemOneResult(
        nouls=nouls or {},
        choices=choices or {},
        scores=scores or {},
        model="jev-1.13.0",
        input_tokens=input_tokens,
    )


def _choice(choice: str, probabilities: dict[str, float]) -> ChoiceResult:
    return ChoiceResult(
        choice=choice, probabilities=probabilities, confidence=max(probabilities.values())
    )


def _method_result(p: float = 0.9) -> SystemOneResult:
    return _result(
        nouls={**{k: p for k in q.METHOD_CLARITY_CRITERIA}, "code_released": 0.92},
        choices={
            "task_type": _choice("language modeling", {"language modeling": 0.8, "other": 0.2}),
            "model_family": _choice("transformer", {"transformer": 0.95, "other": 0.05}),
        },
    )


# --- data availability node -------------------------------------------------------------


class TestDataAvailabilityNode:
    @pytest.mark.asyncio
    async def test_pass_on_public_benchmark(self, context, make_config):
        context.typesafe_client.ask.return_value = _result(
            choices={
                "data_access": _choice(
                    "public benchmark or standard dataset",
                    {"public benchmark or standard dataset": 0.9, "not stated": 0.1},
                )
            }
        )
        result = await score_data_availability_node(_base_state(), make_config)
        dim = result["data_availability_result"]
        assert dim.dimension == "data_availability"
        assert dim.level == 1
        assert dim.derived_score() == 100
        assert dim.probabilities[1] == pytest.approx(1.0)
        assert result["data_availability_usage"] == {"model": "jev-1.13.0", "input_tokens": 1000}

    @pytest.mark.asyncio
    async def test_fail_on_proprietary(self, context, make_config):
        context.typesafe_client.ask.return_value = _result(
            choices={
                "data_access": _choice(
                    "proprietary or private",
                    {
                        "proprietary or private": 0.7,
                        "available on request or under license": 0.2,
                        "not stated": 0.1,
                    },
                )
            }
        )
        result = await score_data_availability_node(_base_state(), make_config)
        dim = result["data_availability_result"]
        assert dim.level == 0
        assert dim.derived_score() == 0
        assert dim.probabilities[0] == pytest.approx(0.9)
        assert dim.evidence and dim.evidence[0].kind == "dataset"
        assert dim.judgments[0].key == "data_access"

    @pytest.mark.asyncio
    async def test_soft_fail_on_unexpected_error(self, context, make_config):
        context.typesafe_client.ask.side_effect = RuntimeError("boom")
        result = await score_data_availability_node(_base_state(), make_config)
        assert result["data_availability_result"] is None
        assert result["data_availability_usage"] is None


# --- demand node ------------------------------------------------------------------------


class TestDemandNode:
    @pytest.mark.parametrize(("band", "expected"), [("HIGH", 85), ("MED", 55), ("LOW", 20)])
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
        assert dim.derived_score() == expected
        assert dim.confidence == 1.0
        assert dim.evidence[0].kind == "citation"
        assert DEMAND_BAND_TO_SCORE[band] == expected

    @pytest.mark.asyncio
    async def test_soft_fail_on_s2_error(self, context, make_config):
        context.semantic_scholar_client.get_citation_metrics.side_effect = RuntimeError("s2 down")
        result = await score_demand_node(_base_state(), make_config)
        assert result["demand_result"] is None


# --- Jev judged nodes -------------------------------------------------------------------


class TestMethodClarityNode:
    @pytest.mark.asyncio
    async def test_happy_combines_nouls_and_attributes(self, context, make_config):
        context.typesafe_client.ask.return_value = _method_result(p=0.9)
        result = await score_method_clarity_node(_base_state(), make_config)

        dim = result["method_clarity_result"]
        assert dim.expected == pytest.approx(3.6)
        assert dim.derived_score() == 90
        assert dim.level == 4
        assert [j.key for j in dim.judgments] == list(q.METHOD_CLARITY_CRITERIA)
        assert dim.evidence[0].kind == "pseudocode"

        attrs = result["attributes_result"]
        assert attrs.code_released.answer is True
        assert attrs.task_type.answer == "language modeling"
        assert attrs.model_family.answer == "transformer"
        assert result["method_clarity_usage"]["input_tokens"] == 1000

        context.typesafe_client.ask.assert_awaited_once()
        payload, questions = context.typesafe_client.ask.call_args.args
        assert set(payload) == {
            "abstract",
            "method",
            "experiments",
            "pseudocode_spans",
            "code_mentions",
        }
        assert set(questions) == set(q.METHOD_CLARITY_CRITERIA) | set(q.ATTRIBUTE_QUESTIONS)

    @pytest.mark.asyncio
    async def test_soft_fail_on_unexpected_error(self, context, make_config):
        context.typesafe_client.ask.side_effect = RuntimeError("bad payload")
        result = await score_method_clarity_node(_base_state(), make_config)
        assert result["method_clarity_result"] is None
        assert result["attributes_result"] is None

    @pytest.mark.asyncio
    async def test_rate_limit_propagates(self, context, make_config):
        context.typesafe_client.ask.side_effect = TypeSafeRateLimitError(retry_after=30)
        with pytest.raises(TypeSafeRateLimitError):
            await score_method_clarity_node(_base_state(), make_config)

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, context, make_config):
        context.typesafe_client.ask.side_effect = TypeSafeConnectionError("timeout")
        with pytest.raises(TypeSafeConnectionError):
            await score_method_clarity_node(_base_state(), make_config)


class TestResourceFeasibilityNode:
    @pytest.mark.asyncio
    async def test_happy_uses_score_distribution(self, context, make_config):
        context.typesafe_client.ask.return_value = _result(
            nouls={"compute_stated": 0.8, "pretrained_weights_released": 0.3},
            scores={
                "compute_tier": ScoreResult(
                    score=3.2,
                    probabilities={0: 0.0, 1: 0.05, 2: 0.15, 3: 0.4, 4: 0.4},
                    confidence=0.4,
                    legend=[lvl for lvl in q.COMPUTE_TIER_LEVELS],
                )
            },
        )
        result = await score_resource_feasibility_node(_base_state(), make_config)
        dim = result["resource_feasibility_result"]
        assert dim.expected == pytest.approx(3.2)
        assert dim.derived_score() == 80
        assert dim.level == 3  # tie between 3 and 4 resolves to the lower level
        assert dim.confidence == pytest.approx(0.4)
        assert [j.key for j in dim.judgments] == [
            "compute_tier",
            "compute_stated",
            "pretrained_weights_released",
        ]
        assert dim.judgments[0].legend == q.COMPUTE_TIER_LEVELS
        assert dim.evidence[0].kind == "compute"

    @pytest.mark.asyncio
    async def test_soft_fail(self, context, make_config):
        context.typesafe_client.ask.side_effect = RuntimeError("bad")
        result = await score_resource_feasibility_node(_base_state(), make_config)
        assert result["resource_feasibility_result"] is None


# --- fetch_and_extract node -------------------------------------------------------------


_RAW_TEXT = """LoRA: Low-Rank Adaptation
Abstract
We propose low-rank adaptation.
1 Introduction
Fine-tuning is expensive.
2 Method
We freeze the weights and inject rank decomposition matrices.
3 Experiments
We train on GLUE with a learning rate of 2e-4 on one A100.
Our code is available at https://github.com/
microsoft/LoRA.
References
[1] Something.
"""


class TestFetchAndExtractNode:
    @pytest.mark.asyncio
    async def test_happy_builds_spans_sections_and_meta(self, context, make_config):
        paper = Mock()
        paper.id = "22222222-2222-2222-2222-222222222222"
        paper.pdf_processed = True
        paper.title = "LoRA"
        paper.abstract = "We propose low-rank adaptation."
        paper.raw_text = _RAW_TEXT
        context.paper_repository.get_by_arxiv_id.return_value = paper
        context.search_service.retrieve_within_paper.return_value = [
            Mock(chunk_text="some relevant chunk"),
        ]

        result = await fetch_and_extract_node({"arxiv_id": "2106.09685"}, make_config)

        context.ingest_service.ingest_by_ids.assert_awaited_once_with(["2106.09685"])
        context.db_session.commit.assert_awaited_once()
        assert context.search_service.retrieve_within_paper.await_count == len(DIMENSION_PROBES)
        assert set(result["extracted_spans"]) == set(DIMENSION_PROBES) | {"code_mentions"}
        assert result["extracted_spans"]["code_mentions"][0] == "https://github.com/microsoft/LoRA"
        assert "rank decomposition" in result["sections"]["method"]
        assert "learning rate" in result["sections"]["experiments"]
        assert result["sections"]["abstract"] == paper.abstract
        assert result["paper_id"] == str(paper.id)
        assert result["paper_meta"]["title"] == "LoRA"

    @pytest.mark.asyncio
    async def test_empty_raw_text_yields_empty_sections(self, context, make_config):
        paper = Mock()
        paper.id = "22222222-2222-2222-2222-222222222222"
        paper.pdf_processed = True
        paper.title = "LoRA"
        paper.abstract = "abs"
        paper.raw_text = None
        context.paper_repository.get_by_arxiv_id.return_value = paper
        context.search_service.retrieve_within_paper.return_value = []

        result = await fetch_and_extract_node({"arxiv_id": "2106.09685"}, make_config)
        assert result["sections"]["method"] == ""
        assert result["extracted_spans"]["code_mentions"] == []

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


def _dim(dimension: str, level: int, max_level: int, expected: float, **kw) -> DimensionScore:
    probs = {lvl: (1.0 if lvl == level else 0.0) for lvl in range(max_level + 1)}
    return DimensionScore(
        dimension=dimension,
        level=level,
        max_level=max_level,
        expected=expected,
        probabilities=probs,
        confidence=1.0,
        judgments=[],
        evidence=kw.get("evidence", []),
        reasoning=kw.get("reasoning", "r"),
    )


class TestComposeNode:
    @pytest.mark.asyncio
    async def test_persists_derived_scores_dimensions_and_usage(self, context, make_config):
        method = _method_result(p=0.8)
        context.typesafe_client.ask.return_value = method
        method_dim = (await score_method_clarity_node(_base_state(), make_config))[
            "method_clarity_result"
        ]
        state = _base_state(
            method_clarity_result=method_dim,
            resource_feasibility_result=None,  # soft-failed
            data_availability_result=_dim(
                "data_availability",
                1,
                1,
                0.95,
                evidence=[EvidenceSpan(text="GLUE", kind="dataset")],
            ),
            demand_result=demand_from_band("MED", [], "steady"),
            attributes_result=None,
            method_clarity_usage={"model": "jev-1.13.0", "input_tokens": 1200},
            resource_feasibility_usage=None,
            data_availability_usage={"model": "jev-1.13.0", "input_tokens": 300},
        )

        await compose_and_persist_node(state, make_config)

        context.scoring_repository.upsert_score.assert_awaited_once()
        kwargs = context.scoring_repository.upsert_score.call_args.kwargs
        assert kwargs["paper_id"] == PAPER_ID
        assert kwargs["rubric_version"] == RUBRIC_VERSION
        assert kwargs["scores"]["method_clarity_score"] == 80
        assert kwargs["scores"]["resource_feasibility_score"] is None
        assert kwargs["scores"]["data_availability_score"] == 100
        assert kwargs["scores"]["demand_score"] == 55
        # JSONB-ready payload: int keys serialized as strings, failed dimension absent
        assert set(kwargs["dimensions"]) == {"method_clarity", "data_availability", "demand"}
        assert "0" in kwargs["dimensions"]["method_clarity"]["probabilities"]
        assert DimensionScore.from_jsonb(kwargs["dimensions"]["method_clarity"]) == method_dim
        assert kwargs["model"] == "jev-1.13.0"
        assert kwargs["input_tokens"] == 1500
        assert kwargs["attributes"] is None
        kinds = {(e["dimension"], e["kind"]) for e in kwargs["evidence"]}
        assert ("data_availability", "dataset") in kinds
        assert ("code_released", "code") in kinds

    @pytest.mark.asyncio
    async def test_attributes_serialized(self, context, make_config):
        context.typesafe_client.ask.return_value = _method_result()
        node_out = await score_method_clarity_node(_base_state(), make_config)
        state = _base_state(
            method_clarity_result=node_out["method_clarity_result"],
            resource_feasibility_result=None,
            data_availability_result=None,
            demand_result=None,
            attributes_result=node_out["attributes_result"],
            method_clarity_usage=node_out["method_clarity_usage"],
            resource_feasibility_usage=None,
            data_availability_usage=None,
        )
        await compose_and_persist_node(state, make_config)
        kwargs = context.scoring_repository.upsert_score.call_args.kwargs
        assert kwargs["attributes"]["code_released"]["answer"] is True
        assert kwargs["attributes"]["task_type"]["answer"] == "language modeling"
