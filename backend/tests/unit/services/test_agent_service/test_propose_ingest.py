"""Tests for ProposeIngestTool."""

import uuid

import pytest
from unittest.mock import AsyncMock

from src.services.agent_service.tools.propose_ingest import ProposeIngestTool, MAX_PROPOSAL


def _make_search_output(papers: list[dict] | None = None) -> dict:
    """Build a fake arxiv_search tool_output entry."""
    return {
        "tool_name": "arxiv_search",
        "data": {
            "count": len(papers) if papers else 0,
            "papers": papers or [],
        },
    }


def _make_paper_meta(arxiv_id: str, title: str = "Test Paper") -> dict:
    """Shorthand for a single paper metadata dict."""
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": ["Author A"],
        "abstract": "An abstract.",
        "published_date": "2026-01-01T00:00:00",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    }


class TestProposeIngestTool:
    """Tests for ProposeIngestTool."""

    @pytest.fixture
    def mock_paper_repository(self):
        repo = AsyncMock()
        # By default, no paper exists yet (batch method returns empty set)
        repo.get_existing_arxiv_ids = AsyncMock(return_value=set())
        return repo

    @pytest.fixture
    def tool(self, mock_paper_repository):
        return ProposeIngestTool(paper_repository=mock_paper_repository)

    # ------------------------------------------------------------------
    # 1. Rejects without prior arxiv_search
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_rejects_without_prior_arxiv_search(self, tool):
        """When tool_outputs has no arxiv_search entry, return a soft error."""
        result = await tool.execute(
            arxiv_ids=["2301.00001"],
            tool_outputs=[],
        )

        assert result.success is False
        assert "prior arxiv_search" in result.error

    # ------------------------------------------------------------------
    # 2. Filters already-ingested papers
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_filters_already_ingested_papers(self, tool, mock_paper_repository):
        """Papers that exist in the repository are excluded from the proposal."""
        # "2301.00001" already ingested, "2301.00002" is new
        mock_paper_repository.get_existing_arxiv_ids = AsyncMock(
            return_value={"2301.00001"}
        )

        search_output = _make_search_output([
            _make_paper_meta("2301.00001", "Already Ingested"),
            _make_paper_meta("2301.00002", "Brand New"),
        ])

        result = await tool.execute(
            arxiv_ids=["2301.00001", "2301.00002"],
            tool_outputs=[search_output],
        )

        assert result.success is True
        proposed_ids = result.data["proposed_ids"]
        assert "2301.00001" not in proposed_ids
        assert "2301.00002" in proposed_ids
        assert len(result.data["papers"]) == 1
        assert result.data["papers"][0]["title"] == "Brand New"

    # ------------------------------------------------------------------
    # 3. Caps at five papers
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_caps_at_five_papers(self, tool):
        """Only the first MAX_PROPOSAL (5) IDs are kept."""
        ids = [f"2301.{i:05d}" for i in range(8)]
        papers = [_make_paper_meta(aid) for aid in ids]
        search_output = _make_search_output(papers)

        result = await tool.execute(
            arxiv_ids=ids,
            tool_outputs=[search_output],
        )

        assert result.success is True
        assert len(result.data["proposed_ids"]) == MAX_PROPOSAL
        assert len(result.data["papers"]) == MAX_PROPOSAL

    # ------------------------------------------------------------------
    # 4. Extracts metadata from prior arxiv_search results
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_extracts_metadata_fromtool_outputs(self, tool):
        """Paper metadata is pulled from the prior arxiv_search output."""
        meta = _make_paper_meta("2301.00001", "Deep Reinforcement Learning")
        meta["authors"] = ["Author X", "Author Y"]
        meta["abstract"] = "A detailed abstract about RL."
        search_output = _make_search_output([meta])

        result = await tool.execute(
            arxiv_ids=["2301.00001"],
            tool_outputs=[search_output],
        )

        assert result.success is True
        paper = result.data["papers"][0]
        assert paper["title"] == "Deep Reinforcement Learning"
        assert paper["authors"] == ["Author X", "Author Y"]
        assert paper["abstract"] == "A detailed abstract about RL."
        assert paper["arxiv_id"] == "2301.00001"

    # ------------------------------------------------------------------
    # 5. Returns empty when all papers are duplicates
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_duplicates(self, tool, mock_paper_repository):
        """When every proposed paper already exists, return an empty proposal."""
        mock_paper_repository.get_existing_arxiv_ids = AsyncMock(
            return_value={"2301.00001", "2301.00002"}
        )

        search_output = _make_search_output([
            _make_paper_meta("2301.00001"),
            _make_paper_meta("2301.00002"),
        ])

        result = await tool.execute(
            arxiv_ids=["2301.00001", "2301.00002"],
            tool_outputs=[search_output],
        )

        assert result.success is True
        assert result.data["papers"] == []
        assert result.data["proposed_ids"] == []
        assert "already in the knowledge base" in result.prompt_text

    # ------------------------------------------------------------------
    # 6. Quota enforcement
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_quota_enforcement(self):
        """When daily ingest count meets the limit, reject with quota message."""
        mock_repo = AsyncMock()
        mock_repo.get_existing_arxiv_ids = AsyncMock(return_value=set())

        mock_usage_repo = AsyncMock()
        mock_usage_repo.get_today_ingest_count = AsyncMock(return_value=10)

        user_id = uuid.uuid4()

        tool = ProposeIngestTool(
            paper_repository=mock_repo,
            daily_ingests=10,
            usage_counter_repo=mock_usage_repo,
            user_id=user_id,
        )

        search_output = _make_search_output([_make_paper_meta("2301.00001")])

        result = await tool.execute(
            arxiv_ids=["2301.00001"],
            tool_outputs=[search_output],
        )

        assert result.success is False
        assert "limit reached" in result.prompt_text.lower()
        # Should not have checked paper existence at all
        mock_repo.get_existing_arxiv_ids.assert_not_called()
