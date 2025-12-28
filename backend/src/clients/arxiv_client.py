"""arXiv API client for fetching papers and PDFs."""

import asyncio
from typing import List, Optional
from datetime import datetime, timezone
import arxiv
import httpx
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


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

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            categories: Optional list of arXiv categories to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            List of ArxivPaper objects
        """
        full_query = query

        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            full_query = f"({query}) AND ({cat_query})"

        log.debug("arxiv search", query=full_query, max_results=max_results)

        search = arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = []
        loop = asyncio.get_event_loop()

        for result in await loop.run_in_executor(None, lambda: list(self.client.results(search))):
            paper = ArxivPaper(result)

            if start_date:
                start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                if paper.published_date < start_dt:
                    continue
            if end_date:
                end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                if paper.published_date > end_dt:
                    continue

            results.append(paper)
            log.debug("arxiv paper found", arxiv_id=paper.arxiv_id, title=paper.title[:60])

            await asyncio.sleep(self.rate_limit_delay)

        log.info("arxiv search complete", query=query[:50], results=len(results))
        return results

    async def download_pdf(self, pdf_url: str, save_path: str) -> str:
        """
        Download PDF from arXiv.

        Args:
            pdf_url: URL to PDF
            save_path: Path to save PDF

        Returns:
            Path to downloaded PDF
        """
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        log.debug("downloading pdf", url=pdf_url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_url, follow_redirects=True)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

        log.debug("pdf downloaded", path=save_path, size_kb=len(response.content) // 1024)
        return save_path

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
        results = []
        loop = asyncio.get_event_loop()

        for result in await loop.run_in_executor(None, lambda: list(self.client.results(search))):
            paper = ArxivPaper(result)
            results.append(paper)
            log.debug("arxiv paper fetched", arxiv_id=paper.arxiv_id)
            await asyncio.sleep(self.rate_limit_delay)

        log.info("arxiv id fetch complete", requested=len(arxiv_ids), found=len(results))
        return results
