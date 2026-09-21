"""Unit tests for Stage 1 triage and the Stage 2 driver task."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.scoring_service.triage import TriageBatchResult, TriageResult


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
        arxiv_crawl_pause_seconds=0,
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
        patch("src.tasks.triage_tasks.get_settings", return_value=triage_settings),
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
            result, _apply_async, generate = _run_triage(
                {"cs.LG": papers}, [batch1, batch2], triage_settings
            )

        assert generate.call_count == 2
        assert result["survivors"] == 25

    def test_global_dedup_across_categories(self):
        settings = SimpleNamespace(
            triage_categories=["cs.LG", "cs.CV"],
            triage_lookback_days=7,
            triage_max_per_category=100,
            arxiv_crawl_pause_seconds=0,
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


class TestScorePaperTask:
    def test_delegates_to_scoring_run(self):
        from src.tasks import score_tasks

        summary = {"status": "scored", "arxiv_id": "2401.001"}
        score_tasks.score_paper_task.push_request(id="test-task-id")
        try:
            with (
                patch.object(score_tasks, "_run", AsyncMock(return_value=summary)) as mock_run,
                patch.object(score_tasks, "release_ondemand_lock") as release,
            ):
                result = score_tasks.score_paper_task._orig_run(arxiv_id="2401.001")
        finally:
            score_tasks.score_paper_task.pop_request()

        assert result == summary
        mock_run.assert_awaited_once_with("2401.001")
        release.assert_called_once_with("2401.001")

    def test_releases_lock_on_hard_failure_but_not_on_rate_limit_retry(self):
        from celery.exceptions import Retry

        from src.exceptions import TypeSafeError, TypeSafeRateLimitError
        from src.tasks import score_tasks

        score_tasks.score_paper_task.push_request(id="test-task-id", retries=0)
        try:
            with (
                patch.object(score_tasks, "_run", AsyncMock(side_effect=TypeSafeError("boom"))),
                patch.object(score_tasks, "release_ondemand_lock") as release,
            ):
                with pytest.raises(TypeSafeError):
                    score_tasks.score_paper_task._orig_run(arxiv_id="2401.001")
            release.assert_called_once_with("2401.001")

            with (
                patch.object(
                    score_tasks,
                    "_run",
                    AsyncMock(side_effect=TypeSafeRateLimitError(retry_after=1)),
                ),
                patch.object(score_tasks, "release_ondemand_lock") as release,
                patch.object(score_tasks.score_paper_task, "retry", side_effect=Retry()),
            ):
                with pytest.raises(Retry):
                    score_tasks.score_paper_task.run(arxiv_id="2401.001")
            release.assert_not_called()
        finally:
            score_tasks.score_paper_task.pop_request()

    def test_release_lock_swallows_redis_errors(self):
        from src.tasks import score_tasks

        with patch.object(score_tasks.redis.Redis, "from_url", side_effect=OSError("down")):
            score_tasks.release_ondemand_lock("2401.001")  # no raise

        client = MagicMock()
        with patch.object(score_tasks.redis.Redis, "from_url", return_value=client):
            score_tasks.release_ondemand_lock("2401.001")
        client.delete.assert_called_once_with("score:ondemand:2401.001")
        client.close.assert_called_once()

    @pytest.mark.parametrize(("retry_after", "countdown"), [(120.0, 120), (5.0, 60), (None, 60)])
    def test_rate_limit_retries_after_server_hint(self, retry_after, countdown):
        from celery.exceptions import Retry

        from src.exceptions import TypeSafeRateLimitError
        from src.tasks import score_tasks

        error = TypeSafeRateLimitError(retry_after=retry_after)
        score_tasks.score_paper_task.push_request(id="test-task-id", retries=0)
        try:
            with (
                patch.object(score_tasks, "_run", AsyncMock(side_effect=error)),
                patch.object(score_tasks, "release_ondemand_lock"),
                patch.object(score_tasks.score_paper_task, "retry", side_effect=Retry()) as retry,
            ):
                with pytest.raises(Retry):
                    score_tasks.score_paper_task.run(arxiv_id="2401.001")
        finally:
            score_tasks.score_paper_task.pop_request()

        retry.assert_called_once()
        assert retry.call_args.kwargs["countdown"] == countdown
        assert retry.call_args.kwargs["exc"] is error

    def test_autoretry_only_for_transient_errors(self):
        from src.exceptions import ScoringError, TypeSafeConnectionError
        from src.tasks import score_tasks

        assert score_tasks.score_paper_task.autoretry_for == (ScoringError, TypeSafeConnectionError)
        assert score_tasks.score_paper_task.retry_backoff == 120
