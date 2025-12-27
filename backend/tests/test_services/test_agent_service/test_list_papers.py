"""Tests for list_papers tool."""

import pytest
from unittest.mock import AsyncMock

from src.services.agent_service.tools.list_papers import ListPapersTool, _parse_date


class TestParseDate:
    """Tests for date parsing helper."""

    def test_valid_date(self):
        result = _parse_date("2024-01-15", "start_date")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_none_returns_none(self):
        assert _parse_date(None, "start_date") is None

    def test_empty_string_returns_none(self):
        assert _parse_date("", "end_date") is None

    def test_invalid_format_raises_with_field_name(self):
        with pytest.raises(ValueError) as exc_info:
            _parse_date("2024-1-5", "start_date")
        assert "start_date" in str(exc_info.value)
        assert "2024-1-5" in str(exc_info.value)
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_format_different_field(self):
        with pytest.raises(ValueError) as exc_info:
            _parse_date("Jan 15, 2024", "end_date")
        assert "end_date" in str(exc_info.value)


class TestListPapersTool:
    """Tests for ListPapersTool."""

    @pytest.fixture
    def mock_ingest_service(self):
        service = AsyncMock()
        service.list_papers.return_value = ([], 0)
        return service

    @pytest.fixture
    def tool(self, mock_ingest_service):
        return ListPapersTool(mock_ingest_service)

    def test_schema_has_single_category(self, tool):
        schema = tool.parameters_schema
        assert "category" in schema["properties"]
        assert "categories" not in schema["properties"]
        assert schema["properties"]["category"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_execute_with_valid_dates(self, tool, mock_ingest_service):
        mock_ingest_service.list_papers.return_value = ([{"title": "Test"}], 1)

        result = await tool.execute(
            query="attention",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        assert result.success is True
        assert result.data["total_count"] == 1
        mock_ingest_service.list_papers.assert_called_once()
        call_args = mock_ingest_service.list_papers.call_args
        assert call_args.kwargs["start_date"].year == 2024
        assert call_args.kwargs["end_date"].month == 12

    @pytest.mark.asyncio
    async def test_execute_with_invalid_start_date(self, tool):
        result = await tool.execute(start_date="2024-1-5")

        assert result.success is False
        assert "start_date" in result.error
        assert "YYYY-MM-DD" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_invalid_end_date(self, tool):
        result = await tool.execute(end_date="not-a-date")

        assert result.success is False
        assert "end_date" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_single_category(self, tool, mock_ingest_service):
        await tool.execute(category="cs.LG")

        call_args = mock_ingest_service.list_papers.call_args
        assert call_args.kwargs["categories"] == ["cs.LG"]

    @pytest.mark.asyncio
    async def test_execute_without_category(self, tool, mock_ingest_service):
        await tool.execute(query="transformers")

        call_args = mock_ingest_service.list_papers.call_args
        assert call_args.kwargs["categories"] is None

    @pytest.mark.asyncio
    async def test_execute_limits_to_50(self, tool, mock_ingest_service):
        await tool.execute(limit=100)

        call_args = mock_ingest_service.list_papers.call_args
        assert call_args.kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, mock_ingest_service):
        mock_ingest_service.list_papers.side_effect = RuntimeError("DB error")

        result = await tool.execute()

        assert result.success is False
        assert "DB error" in result.error
