"""Tests for ArxivClient date-filtered search."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import arxiv
import pytest

from src.clients.arxiv_client import _DATE_FILTER_SCAN_LIMIT, ArxivClient


def _make_result(
    arxiv_id: str,
    published: datetime,
    title: str = "Test Paper",
) -> MagicMock:
    """Build a mock arxiv.Result with the fields ArxivPaper reads."""
    r = MagicMock(spec=arxiv.Result)
    r.entry_id = f"http://arxiv.org/abs/{arxiv_id}v1"
    r.title = title
    r.authors = []
    r.summary = "abstract"
    r.categories = ["cs.CL"]
    r.published = published
    r.pdf_url = f"http://arxiv.org/pdf/{arxiv_id}v1"
    r.updated = published
    return r


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


# Papers spanning Feb 8-16, sorted descending (like arXiv would return).
_PAPERS = [
    _make_result("2602.99005", _utc(2026, 2, 16), "Paper Feb 16"),
    _make_result("2602.99004", _utc(2026, 2, 15), "Paper Feb 15"),
    _make_result("2602.99003", _utc(2026, 2, 14), "Paper Feb 14"),
    _make_result("2602.99002", _utc(2026, 2, 10), "Paper Feb 10"),
    _make_result("2602.99001", _utc(2026, 2, 8), "Paper Feb 8"),
]


@pytest.fixture
def client() -> ArxivClient:
    return ArxivClient(rate_limit_delay=0.0)


class TestDateFilteredSearchEarlyTermination:
    """Verify the lazy iterator stops once past the date window."""

    @pytest.mark.asyncio
    async def test_stops_at_paper_before_start_date(self, client: ArxivClient):
        """Feed 5 papers Feb 8-16, filter start_date=Feb 13.

        Should collect Feb 14 and Feb 15 (Feb 16 is after end_date),
        then hit Feb 10 which is before start_date and stop -- never
        reaching Feb 8.
        """
        consumed: list[MagicMock] = []

        def tracking_generator(search: arxiv.Search):
            for paper in _PAPERS:
                consumed.append(paper)
                yield paper

        with patch.object(client.client, "results", side_effect=tracking_generator):
            results = await client.search_papers(
                query="large language models",
                max_results=10,
                start_date="2026-02-13",
                end_date="2026-02-15",
            )

        # Should return Feb 15 and Feb 14 (Feb 16 is outside end_date)
        assert len(results) == 2
        ids = [p.arxiv_id for p in results]
        assert "2602.99004" in ids  # Feb 15
        assert "2602.99003" in ids  # Feb 14

        # Early termination: consumed Feb 16, 15, 14, then 10 triggers stop.
        # Should NOT have reached Feb 8.
        assert len(consumed) == 4

    @pytest.mark.asyncio
    async def test_collects_up_to_max_results(self, client: ArxivClient):
        """When max_results is reached, stop even if more papers are in range."""
        all_in_range = [
            _make_result(f"2602.0000{i}", _utc(2026, 2, 15 - i), f"Paper {i}") for i in range(5)
        ]

        with patch.object(client.client, "results", return_value=iter(all_in_range)):
            results = await client.search_papers(
                query="transformers",
                max_results=2,
                start_date="2026-02-01",
                end_date="2026-02-28",
            )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_skips_papers_after_end_date_without_stopping(self, client: ArxivClient):
        """Papers newer than end_date are skipped but don't trigger early stop."""
        papers = [
            _make_result("2602.99010", _utc(2026, 2, 20), "Too new"),
            _make_result("2602.99009", _utc(2026, 2, 18), "Also too new"),
            _make_result("2602.99003", _utc(2026, 2, 14), "In range"),
        ]

        with patch.object(client.client, "results", return_value=iter(papers)):
            results = await client.search_papers(
                query="attention",
                max_results=10,
                start_date="2026-02-13",
                end_date="2026-02-15",
            )

        assert len(results) == 1
        assert results[0].arxiv_id == "2602.99003"

    @pytest.mark.asyncio
    async def test_empty_results(self, client: ArxivClient):
        """Returns empty list when no papers match the date window."""
        papers = [
            _make_result("2602.99001", _utc(2026, 2, 1), "Too old"),
        ]

        with patch.object(client.client, "results", return_value=iter(papers)):
            results = await client.search_papers(
                query="quantum computing",
                max_results=10,
                start_date="2026-02-14",
                end_date="2026-02-14",
            )

        assert results == []


class TestDateFilteredSearchConfig:
    """Verify the search is configured correctly for date-filtered queries."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("max_results", "expected_scan"),
        [(5, 15), (100, 300), (500, _DATE_FILTER_SCAN_LIMIT)],
    )
    async def test_search_scan_limit_scales_with_request(
        self, client: ArxivClient, max_results: int, expected_scan: int
    ):
        """The scan cap is 3x the request, never above _DATE_FILTER_SCAN_LIMIT (SPE-283)."""
        captured_search: list[arxiv.Search] = []

        def capture_search(search: arxiv.Search):
            captured_search.append(search)
            return iter([])

        with patch.object(client.client, "results", side_effect=capture_search):
            await client.search_papers(
                query="nlp",
                max_results=max_results,
                start_date="2026-02-14",
            )

        assert len(captured_search) == 1
        assert captured_search[0].max_results == expected_scan

    @pytest.mark.asyncio
    async def test_search_sorted_by_date_descending(self, client: ArxivClient):
        """Date-filtered searches must sort by SubmittedDate descending."""
        captured_search: list[arxiv.Search] = []

        def capture_search(search: arxiv.Search):
            captured_search.append(search)
            return iter([])

        with patch.object(client.client, "results", side_effect=capture_search):
            await client.search_papers(
                query="nlp",
                max_results=5,
                start_date="2026-02-14",
            )

        assert captured_search[0].sort_by == arxiv.SortCriterion.SubmittedDate
        assert captured_search[0].sort_order == arxiv.SortOrder.Descending


class TestNonDateSearch:
    """Ensure non-date searches are unaffected by the refactor."""

    @pytest.mark.asyncio
    async def test_non_date_search_uses_relevance_sort(self, client: ArxivClient):
        """Without date filters, search should sort by Relevance."""
        captured_search: list[arxiv.Search] = []

        def capture_search(search: arxiv.Search):
            captured_search.append(search)
            return iter([])

        with patch.object(client.client, "results", side_effect=capture_search):
            await client.search_papers(query="machine learning", max_results=5)

        assert captured_search[0].sort_by == arxiv.SortCriterion.Relevance
        assert captured_search[0].max_results == 5


class TestGetPaperById:
    """The read-path single-id fetch: one id_list query, no pacing sleep."""

    @pytest.mark.asyncio
    async def test_returns_paper_without_sleeping(self):
        client = ArxivClient(rate_limit_delay=3.0)
        captured: list[arxiv.Search] = []

        def capture(search: arxiv.Search):
            captured.append(search)
            return iter([_make_result("2602.99001", _utc(2026, 2, 8), "Found")])

        with (
            patch.object(client.client, "results", side_effect=capture),
            patch("src.clients.arxiv_client.asyncio.sleep") as sleep,
        ):
            paper = await client.get_paper_by_id("2602.99001")

        assert paper is not None and paper.arxiv_id == "2602.99001" and paper.title == "Found"
        assert captured[0].id_list == ["2602.99001"] and captured[0].max_results == 1
        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_id_is_none(self, client: ArxivClient):
        with patch.object(client.client, "results", return_value=iter([])):
            assert await client.get_paper_by_id("2602.00000") is None
