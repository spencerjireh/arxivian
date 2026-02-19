"""Unit tests for IngestPapersTool daily quota enforcement."""

import uuid

import pytest
from unittest.mock import AsyncMock

from src.schemas.ingest import IngestResponse, PaperResult
from src.services.agent_service.tools.ingest import IngestPapersTool


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_usage_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ingest_service() -> AsyncMock:
    service = AsyncMock()
    service.ingest_papers = AsyncMock(
        return_value=IngestResponse(
            status="completed",
            papers_fetched=2,
            papers_processed=2,
            chunks_created=20,
            duration_seconds=1.0,
            errors=[],
            papers=[
                PaperResult(
                    arxiv_id="2301.00001",
                    title="Paper A",
                    chunks_created=10,
                    status="success",
                ),
                PaperResult(
                    arxiv_id="2301.00002",
                    title="Paper B",
                    chunks_created=10,
                    status="success",
                ),
            ],
        )
    )
    return service


class TestIngestToolQuota:
    """Tests for daily ingest quota enforcement in IngestPapersTool."""

    @pytest.mark.asyncio
    async def test_limit_reached_returns_error(self, mock_ingest_service, mock_usage_repo, user_id):
        """When today's count already equals the daily cap, reject immediately."""
        mock_usage_repo.get_today_ingest_count = AsyncMock(return_value=10)

        tool = IngestPapersTool(
            ingest_service=mock_ingest_service,
            daily_ingests=10,
            usage_counter_repo=mock_usage_repo,
            user_id=user_id,
        )

        result = await tool.execute(query="transformers", max_results=5)

        assert result.success is False
        assert "limit reached" in result.prompt_text.lower()
        mock_ingest_service.ingest_papers.assert_not_called()

    @pytest.mark.asyncio
    async def test_requested_exceeds_remaining_returns_error(
        self, mock_ingest_service, mock_usage_repo, user_id
    ):
        """When max_results > remaining quota, reject with remaining count."""
        mock_usage_repo.get_today_ingest_count = AsyncMock(return_value=7)

        tool = IngestPapersTool(
            ingest_service=mock_ingest_service,
            daily_ingests=10,
            usage_counter_repo=mock_usage_repo,
            user_id=user_id,
        )

        result = await tool.execute(query="transformers", max_results=5)

        assert result.success is False
        assert "3" in result.prompt_text  # 10 - 7 = 3 remaining

    @pytest.mark.asyncio
    async def test_unlimited_skips_quota_check(
        self, mock_ingest_service, mock_usage_repo, user_id
    ):
        """When daily_ingests is None (pro tier), quota check is skipped entirely."""
        tool = IngestPapersTool(
            ingest_service=mock_ingest_service,
            daily_ingests=None,
            usage_counter_repo=mock_usage_repo,
            user_id=user_id,
        )

        result = await tool.execute(query="transformers", max_results=5)

        assert result.success is True
        mock_usage_repo.get_today_ingest_count.assert_not_called()
        mock_ingest_service.ingest_papers.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_ingest_increments_counter(
        self, mock_ingest_service, mock_usage_repo, user_id
    ):
        """After a successful ingest, usage counter is incremented by papers_processed."""
        mock_usage_repo.get_today_ingest_count = AsyncMock(return_value=0)

        tool = IngestPapersTool(
            ingest_service=mock_ingest_service,
            daily_ingests=10,
            usage_counter_repo=mock_usage_repo,
            user_id=user_id,
        )

        result = await tool.execute(query="transformers", max_results=5)

        assert result.success is True
        mock_usage_repo.increment_ingest_count.assert_called_once_with(user_id, 2)
