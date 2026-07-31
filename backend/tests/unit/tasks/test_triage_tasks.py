"""Unit tests for Stage 1 triage and the Stage 2 stub task."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.schemas.triage import TriageBatchResult, TriageResult


def _paper(arxiv_id: str, title: str = "T", abstract: str = "A", categories=None):
    """Minimal ArxivPaper-like object (only the fields triage reads)."""
    return SimpleNamespace(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        categories=categories or ["cs.LG"],
    )


def _verdict(arxiv_id: str, keep: bool):
    return TriageResult(
        arxiv_id=arxiv_id,
        paper_class="method" if keep else "survey",
        rough_implementability=80 if keep else 10,
        keep=keep,
        reasoning="because",
    )


@pytest.fixture
def triage_settings():
    """Settings stub for the triage task."""
    return SimpleNamespace(
        triage_categories=["cs.LG"],
        triage_lookback_days=7,
        triage_max_per_category=100,
    )


def _run_triage(crawl_by_category, batch_results, triage_settings):
    """Invoke triage_new_papers_task with mocked crawl + LLM + Stage 2 enqueue.

    Args:
        crawl_by_category: dict category -> list of ArxivPaper-like objects.
        batch_results: list of TriageBatchResult (or Exception) returned per batch call.

    Returns:
        (result_dict, mock_apply_async, mock_generate_structured).
    """
    from src.tasks.triage_tasks import triage_new_papers_task

    async def _search(query, categories, max_results, start_date, end_date):
        return crawl_by_category.get(categories[0], [])

    mock_arxiv = Mock()
    mock_arxiv.search_papers = AsyncMock(side_effect=_search)

    mock_generate = AsyncMock(side_effect=batch_results)
    mock_llm = Mock()
    mock_llm.generate_structured = mock_generate

    mock_apply_async = Mock(return_value=Mock(id="stage2-id"))

    with (
        patch("src.tasks.triage_tasks.get_arxiv_client", return_value=mock_arxiv),
        patch("src.tasks.triage_tasks.get_llm_client", return_value=mock_llm),
        patch("src.config.get_settings", return_value=triage_settings),
        patch("src.tasks.triage_tasks.score_paper_task") as mock_score_task,
    ):
        mock_score_task.apply_async = mock_apply_async
        result = triage_new_papers_task()

    return result, mock_apply_async, mock_generate


class TestTriageNewPapersTask:
    def test_enqueues_only_survivors(self, triage_settings):
        papers = [_paper("2401.001"), _paper("2401.002"), _paper("2401.003")]
        batch = TriageBatchResult(
            results=[
                _verdict("2401.001", True),
                _verdict("2401.002", False),
                _verdict("2401.003", True),
            ]
        )
        result, apply_async, _ = _run_triage({"cs.LG": papers}, [batch], triage_settings)

        assert result["status"] == "completed"
        assert result["crawled"] == 3
        assert result["survivors"] == 2
        assert result["rejected"] == 1
        assert apply_async.call_count == 2
        enqueued_ids = {c.kwargs["kwargs"]["arxiv_id"] for c in apply_async.call_args_list}
        assert enqueued_ids == {"2401.001", "2401.003"}

    def test_deterministic_task_ids_are_stable_and_truncated(self, triage_settings):
        papers = [_paper("2401.001")]
        batch = TriageBatchResult(results=[_verdict("2401.001", True)])

        _, apply_async1, _ = _run_triage({"cs.LG": papers}, [batch], triage_settings)
        # second run needs a fresh batch result (side_effect is consumed)
        batch2 = TriageBatchResult(results=[_verdict("2401.001", True)])
        _, apply_async2, _ = _run_triage({"cs.LG": papers}, [batch2], triage_settings)

        id1 = apply_async1.call_args.kwargs["task_id"]
        id2 = apply_async2.call_args.kwargs["task_id"]
        assert len(id1) == 32
        assert id1 == id2  # same date + category + arxiv_id -> same id

    def test_staggered_countdown(self, triage_settings):
        papers = [_paper("2401.001"), _paper("2401.002")]
        batch = TriageBatchResult(results=[_verdict("2401.001", True), _verdict("2401.002", True)])
        _, apply_async, _ = _run_triage({"cs.LG": papers}, [batch], triage_settings)

        countdowns = [c.kwargs["countdown"] for c in apply_async.call_args_list]
        assert countdowns == [0, 5]  # STAGGER_SECONDS = 5

    def test_batches_split_by_batch_size(self, triage_settings):
        papers = [_paper(f"2401.{i:03d}") for i in range(25)]
        # 25 papers, batch size 20 -> 2 batches
        batch1 = TriageBatchResult(results=[_verdict(f"2401.{i:03d}", True) for i in range(20)])
        batch2 = TriageBatchResult(results=[_verdict(f"2401.{i:03d}", True) for i in range(20, 25)])

        with patch("src.tasks.triage_tasks.TRIAGE_BATCH_SIZE", 20):
            result, apply_async, generate = _run_triage(
                {"cs.LG": papers}, [batch1, batch2], triage_settings
            )

        assert generate.call_count == 2
        assert result["survivors"] == 25

    def test_global_dedup_across_categories(self):
        settings = SimpleNamespace(
            triage_categories=["cs.LG", "cs.CV"],
            triage_lookback_days=7,
            triage_max_per_category=100,
        )
        # 2401.001 is cross-listed in both categories.
        crawl = {
            "cs.LG": [_paper("2401.001"), _paper("2401.002")],
            "cs.CV": [_paper("2401.001"), _paper("2401.003")],
        }
        batch = TriageBatchResult(
            results=[
                _verdict("2401.001", True),
                _verdict("2401.002", True),
                _verdict("2401.003", True),
            ]
        )
        result, apply_async, _ = _run_triage(crawl, [batch], settings)

        assert result["crawled"] == 3  # deduped, not 4
        assert apply_async.call_count == 3

    def test_batch_failure_is_skipped(self, triage_settings):
        papers = [_paper("2401.001"), _paper("2401.002")]
        result, apply_async, _ = _run_triage(
            {"cs.LG": papers}, [RuntimeError("llm down")], triage_settings
        )

        # No verdicts -> nothing enqueued, nothing counted as rejected.
        assert result["survivors"] == 0
        assert result["rejected"] == 0
        assert result["crawled"] == 2
        apply_async.assert_not_called()


class TestScorePaperTaskStub:
    def test_stub_returns_arxiv_id(self):
        from src.tasks.score_tasks import score_paper_task

        score_paper_task.push_request(id="test-task-id")
        try:
            result = score_paper_task._orig_run(arxiv_id="2401.001")
        finally:
            score_paper_task.pop_request()
        assert result == {"status": "stub", "arxiv_id": "2401.001"}
