"""arXiv API client for fetching papers and PDFs."""

import asyncio
import re
from typing import List, Optional
from datetime import datetime, timezone
import arxiv
import httpx
from pathlib import Path
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from src.utils.logger import get_logger
from src.exceptions import ArxivAPIError

log = get_logger(__name__)
_tenacity_logger = logging.getLogger(__name__)

# When date filters are active, fetch extra results to filter client-side
# (the arXiv API silently ignores submittedDate when combined with keywords).
_DATE_FILTER_FETCH_COUNT = 30


class ArxivPaper:
    """arXiv paper metadata."""

    def __init__(self, entry: arxiv.Result):
        self.arxiv_id = entry.entry_id.split("/")[-1].split("v")[0]
        self.title = entry.title
        self.authors = [author.name for author in entry.authors]
        self.abstract = entry.summary
        self.categories = entry.categories
        self.published_date = entry.published
        self.pdf_url = entry.pdf_url
        self.updated_date = entry.updated


class ArxivClient:
    """Client for interacting with arXiv API."""

    def __init__(self, rate_limit_delay: float = 3.0):
        """
        Initialize arXiv client.

        Args:
            rate_limit_delay: Seconds to wait between requests (arXiv guideline: 3s)
        """
        self.rate_limit_delay = rate_limit_delay
        self.client = arxiv.Client()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (
                arxiv.HTTPError,
                arxiv.UnexpectedEmptyPageError,
                ConnectionError,
                TimeoutError,
            )
        ),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    def _execute_search_sync(self, search: arxiv.Search) -> List[arxiv.Result]:
        """
        Execute arXiv search synchronously with retry logic.

        Args:
            search: arXiv Search object

        Returns:
            List of arxiv.Result objects

        Raises:
            ArxivAPIError: If search fails after retries
        """
        try:
            return list(self.client.results(search))
        except Exception as e:
            log.warning("arxiv search attempt failed", error=str(e), error_type=type(e).__name__)
            raise

    async def _execute_search(self, search: arxiv.Search) -> List[arxiv.Result]:
        """
        Execute arXiv search asynchronously with retry logic.

        Args:
            search: arXiv Search object

        Returns:
            List of arxiv.Result objects

        Raises:
            ArxivAPIError: If search fails after all retries
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._execute_search_sync, search)
        except Exception as e:
            raise ArxivAPIError(
                message=f"arXiv search failed after retries: {str(e)}",
                details={"query": str(search.query), "error_type": type(e).__name__},
            )

    # Matches bare submittedDate:YYYY-MM-DD or submittedDate:YYYYMMDD in a query.
    # Does NOT match the valid range form submittedDate:[... TO ...].
    _BARE_DATE_RE = re.compile(
        r"(?:\s*(?:AND|OR)\s+)?"  # optional leading boolean operator
        r"submittedDate:(\d{4}-?\d{2}-?\d{2})"
        r"(?:\s+(?:AND|OR)\s*)?",  # optional trailing boolean operator
        re.IGNORECASE,
    )

    @staticmethod
    def _date_to_arxiv_fmt(date_str: str, end_of_day: bool = False) -> str:
        """Convert a YYYY-MM-DD string to arXiv YYYYMMDDHHNN format."""
        dt = datetime.fromisoformat(date_str)
        suffix = "2359" if end_of_day else "0000"
        return dt.strftime("%Y%m%d") + suffix

    @classmethod
    def _sanitize_query(cls, query: str) -> tuple[str, str | None]:
        """Extract bare submittedDate: terms from the query and convert to range syntax.

        LLMs often produce invalid forms like ``submittedDate:2026-02-14`` which
        cause HTTP 500 from the arXiv API.  The only valid syntax is the bracket
        range: ``submittedDate:[YYYYMMDD0000 TO YYYYMMDD2359]``.

        All bare submittedDate: terms are stripped from the query, but only the
        first match is used for the returned date clause.

        Returns:
            (cleaned_query, date_clause | None)
        """
        match = cls._BARE_DATE_RE.search(query)
        if not match:
            return query, None

        raw_date = match.group(1)
        cleaned = cls._BARE_DATE_RE.sub(" ", query).strip()
        # Remove dangling boolean operators left at the edges
        cleaned = re.sub(r"^\s*(AND|OR)\s+", "", cleaned)
        cleaned = re.sub(r"\s+(AND|OR)\s*$", "", cleaned)

        # Normalise to YYYY-MM-DD for fromisoformat
        if "-" in raw_date:
            normalised = raw_date
        else:
            normalised = (
                f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            )
        low = cls._date_to_arxiv_fmt(normalised)
        high = cls._date_to_arxiv_fmt(normalised, end_of_day=True)
        date_clause = f"submittedDate:[{low} TO {high}]"

        log.debug(
            "sanitized bare submittedDate in query",
            original=raw_date,
            clause=date_clause,
        )
        return cleaned, date_clause

    @staticmethod
    def _paper_in_date_range(
        paper: ArxivPaper,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
    ) -> bool:
        """Check whether a paper's published_date falls within the date range."""
        pub = paper.published_date
        if pub is None:
            return False
        pub_date = pub.date()
        if start_dt and pub_date < start_dt.date():
            return False
        if end_dt and pub_date > end_dt.date():
            return False
        return True

    async def search_papers(
        self,
        query: str,
        max_results: int = 10,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ArxivPaper]:
        """
        Search arXiv for papers matching criteria.

        When date filters are provided the arXiv API's submittedDate clause is
        NOT appended (it is silently ignored when combined with keyword search).
        Instead we sort by SubmittedDate descending, over-fetch, and filter
        client-side.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            categories: Optional list of arXiv categories to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            List of ArxivPaper objects
        """
        has_date_filter = bool(start_date or end_date)

        # Parse date strings once for client-side filtering (must be tz-aware
        # because ArxivPaper.published_date comes from the API as UTC)
        start_dt = (
            datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            if start_date else None
        )
        end_dt = (
            datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
            if end_date else None
        )

        # Sanitize any bare submittedDate: terms the LLM put in the query
        full_query, extracted_date = self._sanitize_query(query)

        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            full_query = f"({full_query}) AND ({cat_query})" if full_query else cat_query

        # Only append date clause when there is NO keyword search
        # (the arXiv API ignores submittedDate when combined with keywords)
        if not has_date_filter:
            date_clause = extracted_date
            if date_clause:
                full_query = f"({full_query}) AND {date_clause}" if full_query else date_clause

        # When date-filtering, sort by date and over-fetch so we have enough
        # results after client-side filtering
        if has_date_filter:
            sort_by = arxiv.SortCriterion.SubmittedDate
            sort_order = arxiv.SortOrder.Descending
            fetch_count = _DATE_FILTER_FETCH_COUNT
        else:
            sort_by = arxiv.SortCriterion.Relevance
            sort_order = arxiv.SortOrder.Descending
            fetch_count = max_results

        log.debug(
            "arxiv search",
            query=full_query,
            max_results=fetch_count,
            sort_by=sort_by.value,
            date_filter=has_date_filter,
        )

        search = arxiv.Search(
            query=full_query,
            max_results=fetch_count,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        raw_results = await self._execute_search(search)

        results = []
        for result in raw_results:
            paper = ArxivPaper(result)
            if has_date_filter and not self._paper_in_date_range(paper, start_dt, end_dt):
                continue
            results.append(paper)
            log.debug("arxiv paper found", arxiv_id=paper.arxiv_id, title=paper.title[:60])
            if len(results) >= max_results:
                break

        log.info(
            "arxiv search complete",
            query=query[:50],
            results=len(results),
            fetched=len(raw_results),
            date_filtered=has_date_filter,
        )
        return results

    async def download_pdf(self, pdf_url: str, save_path: str) -> str:
        """
        Download PDF from arXiv with retry logic.

        Args:
            pdf_url: URL to PDF
            save_path: Path to save PDF

        Returns:
            Path to downloaded PDF

        Raises:
            ArxivAPIError: If download fails after retries
        """
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        log.debug("downloading pdf", url=pdf_url)

        # Use tenacity for async retry
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(
                (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
            ),
            before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
            reraise=True,
        )
        async def _download_with_retry() -> bytes:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(pdf_url, follow_redirects=True)
                response.raise_for_status()
                return response.content

        try:
            content = await _download_with_retry()
            with open(save_path, "wb") as f:
                f.write(content)
            log.debug("pdf downloaded", path=save_path, size_kb=len(content) // 1024)
            return save_path
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as e:
            raise ArxivAPIError(
                message=f"PDF download failed after retries: {str(e)}",
                details={"url": pdf_url, "error_type": type(e).__name__},
            )

    async def get_papers_by_ids(self, arxiv_ids: List[str]) -> List[ArxivPaper]:
        """
        Fetch papers by arXiv IDs.

        Args:
            arxiv_ids: List of arXiv paper IDs (e.g., ["2301.00001", "2312.12345"])

        Returns:
            List of ArxivPaper objects
        """
        log.debug("arxiv fetch by ids", count=len(arxiv_ids))

        search = arxiv.Search(id_list=arxiv_ids)

        # Use retry-enabled helper
        raw_results = await self._execute_search(search)

        results = []
        for result in raw_results:
            paper = ArxivPaper(result)
            results.append(paper)
            log.debug("arxiv paper fetched", arxiv_id=paper.arxiv_id)
            await asyncio.sleep(self.rate_limit_delay)

        log.info("arxiv id fetch complete", requested=len(arxiv_ids), found=len(results))
        return results
