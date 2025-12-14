"""arXiv API client for fetching papers and PDFs."""

import asyncio
from typing import List, Optional
from datetime import datetime
import arxiv
import httpx
from pathlib import Path


class ArxivPaper:
    """arXiv paper metadata."""

    def __init__(self, entry: arxiv.Result):
        self.arxiv_id = entry.entry_id.split("/")[-1].split("v")[0]  # Remove version
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
        # Build query with filters
        full_query = query

        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            full_query = f"({query}) AND ({cat_query})"

        # Create search
        search = arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        # Execute search (run in thread pool since arxiv lib is sync)
        results = []
        loop = asyncio.get_event_loop()

        for result in await loop.run_in_executor(
            None, lambda: list(self.client.results(search))
        ):
            paper = ArxivPaper(result)

            # Filter by date if specified
            if start_date and paper.published_date < datetime.fromisoformat(start_date):
                continue
            if end_date and paper.published_date > datetime.fromisoformat(end_date):
                continue

            results.append(paper)

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

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
        # Ensure directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_url, follow_redirects=True)
            response.raise_for_status()

            # Save to file
            with open(save_path, "wb") as f:
                f.write(response.content)

        return save_path
