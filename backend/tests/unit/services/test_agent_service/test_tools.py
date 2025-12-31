"""Tests for agent tools."""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import ClassVar

from src.services.agent_service.tools import (
    BaseTool,
    ToolResult,
    ToolRegistry,
    RetrieveChunksTool,
    IngestPapersTool,
    ArxivSearchTool,
    ExploreCitationsTool,
    SummarizePaperTool,
)
from src.services.agent_service.tools.retrieve import MAX_TOP_K


class TestRetrieveChunksTool:
    """Tests for RetrieveChunksTool."""

    @pytest.fixture
    def mock_search_service(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_search_service):
        return RetrieveChunksTool(search_service=mock_search_service, default_top_k=6)

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, tool):
        result = await tool.execute(query="")
        assert result.success is False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_error(self, tool):
        result = await tool.execute(query="   ")
        assert result.success is False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_top_k_clamped_to_max(self, tool, mock_search_service):
        mock_search_service.hybrid_search.return_value = []

        await tool.execute(query="test", top_k=100)

        call_args = mock_search_service.hybrid_search.call_args
        assert call_args.kwargs["top_k"] == MAX_TOP_K

    @pytest.mark.asyncio
    async def test_top_k_minimum_is_one(self, tool, mock_search_service):
        mock_search_service.hybrid_search.return_value = []

        await tool.execute(query="test", top_k=0)

        call_args = mock_search_service.hybrid_search.call_args
        assert call_args.kwargs["top_k"] == 1

    @pytest.mark.asyncio
    async def test_successful_retrieval(self, tool, mock_search_service):
        mock_result = Mock()
        mock_result.chunk_id = "chunk-1"
        mock_result.chunk_text = "Test content"
        mock_result.arxiv_id = "2301.00001"
        mock_result.title = "Test Paper"
        mock_result.authors = ["Author One"]
        mock_result.section_name = "Introduction"
        mock_result.score = 0.95
        mock_result.pdf_url = "https://arxiv.org/pdf/2301.00001.pdf"
        mock_result.published_date = "2023-01-01"

        mock_search_service.hybrid_search.return_value = [mock_result]

        result = await tool.execute(query="transformers")

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["arxiv_id"] == "2301.00001"
        assert result.data[0]["authors"] == ["Author One"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, tool, mock_search_service):
        mock_search_service.hybrid_search.side_effect = Exception("Database error")

        result = await tool.execute(query="test")

        assert result.success is False
        assert "Database error" in result.error

    def test_class_variables(self, tool):
        assert tool.result_key is None
        assert tool.extends_chunks is True
        assert "search_service" in tool.required_dependencies


class TestIngestPapersTool:
    """Tests for IngestPapersTool."""

    @pytest.fixture
    def mock_ingest_service(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_ingest_service):
        return IngestPapersTool(ingest_service=mock_ingest_service)

    @pytest.mark.asyncio
    async def test_both_query_and_ids_returns_error(self, tool):
        result = await tool.execute(query="test", arxiv_ids=["2301.00001"])
        assert result.success is False
        assert "not both" in result.error.lower()

    @pytest.mark.asyncio
    async def test_neither_query_nor_ids_returns_error(self, tool):
        result = await tool.execute()
        assert result.success is False
        assert "must provide" in result.error.lower()

    def test_class_variables(self, tool):
        assert tool.result_key == "ingest_papers_results"
        assert tool.extends_chunks is False
        assert "ingest_service" in tool.required_dependencies


class TestArxivSearchTool:
    """Tests for ArxivSearchTool."""

    @pytest.fixture
    def mock_arxiv_client(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_arxiv_client):
        return ArxivSearchTool(arxiv_client=mock_arxiv_client)

    @pytest.mark.asyncio
    async def test_max_results_clamped_to_10(self, tool, mock_arxiv_client):
        mock_arxiv_client.search_papers.return_value = []

        await tool.execute(query="test", max_results=20)

        call_args = mock_arxiv_client.search_papers.call_args
        assert call_args.kwargs["max_results"] == 10

    @pytest.mark.asyncio
    async def test_max_results_minimum_is_one(self, tool, mock_arxiv_client):
        mock_arxiv_client.search_papers.return_value = []

        await tool.execute(query="test", max_results=0)

        call_args = mock_arxiv_client.search_papers.call_args
        assert call_args.kwargs["max_results"] == 1

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, tool):
        result = await tool.execute(query="test", start_date="invalid")
        assert result.success is False
        assert "Invalid" in result.error

    def test_class_variables(self, tool):
        assert tool.result_key == "arxiv_search_results"
        assert tool.extends_chunks is False
        assert "arxiv_client" in tool.required_dependencies


class TestExploreCitationsTool:
    """Tests for ExploreCitationsTool."""

    @pytest.fixture
    def mock_paper_repository(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_paper_repository):
        return ExploreCitationsTool(paper_repository=mock_paper_repository)

    @pytest.mark.asyncio
    async def test_paper_not_found(self, tool, mock_paper_repository):
        mock_paper_repository.get_by_arxiv_id.return_value = None

        result = await tool.execute(arxiv_id="nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_paper_not_processed(self, tool, mock_paper_repository):
        mock_paper = Mock()
        mock_paper.pdf_processed = False
        mock_paper_repository.get_by_arxiv_id.return_value = mock_paper

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is False
        assert "not been processed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_successful_citation_retrieval(self, tool, mock_paper_repository):
        mock_paper = Mock()
        mock_paper.arxiv_id = "2301.00001"
        mock_paper.title = "Test Paper"
        mock_paper.pdf_processed = True
        mock_paper.references = ["Reference 1", "Reference 2"]
        mock_paper_repository.get_by_arxiv_id.return_value = mock_paper

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is True
        assert result.data["reference_count"] == 2

    def test_class_variables(self, tool):
        assert tool.result_key == "explore_citations_results"
        assert tool.extends_chunks is False
        assert "paper_repository" in tool.required_dependencies


class TestSummarizePaperTool:
    """Tests for SummarizePaperTool."""

    @pytest.fixture
    def mock_paper_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_paper_repository, mock_llm_client):
        return SummarizePaperTool(
            paper_repository=mock_paper_repository, llm_client=mock_llm_client
        )

    @pytest.mark.asyncio
    async def test_paper_not_found(self, tool, mock_paper_repository):
        mock_paper_repository.get_by_arxiv_id.return_value = None

        result = await tool.execute(arxiv_id="nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_paper_not_processed(self, tool, mock_paper_repository):
        mock_paper = Mock()
        mock_paper.pdf_processed = False
        mock_paper_repository.get_by_arxiv_id.return_value = mock_paper

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is False
        assert "not been processed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_successful_summary(self, tool, mock_paper_repository, mock_llm_client):
        mock_paper = Mock()
        mock_paper.arxiv_id = "2301.00001"
        mock_paper.title = "Test Paper"
        mock_paper.abstract = "This is a test abstract."
        mock_paper.pdf_processed = True
        mock_paper_repository.get_by_arxiv_id.return_value = mock_paper
        mock_llm_client.generate_completion.return_value = "Summary text"

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is True
        assert result.data["summary"] == "Summary text"

    def test_class_variables(self, tool):
        assert tool.result_key == "summarize_paper_results"
        assert tool.extends_chunks is False
        assert "paper_repository" in tool.required_dependencies
        assert "llm_client" in tool.required_dependencies


class TestToolRegistry:
    """Tests for ToolRegistry dependency validation."""

    def test_register_tool_with_all_dependencies(self):
        """Tool with all required dependencies registers successfully."""
        registry = ToolRegistry()

        class ValidTool(BaseTool):
            name = "valid_tool"
            description = "A valid tool"
            required_dependencies: ClassVar[list[str]] = ["my_service"]

            def __init__(self, my_service):
                self.my_service = my_service

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data=None, tool_name=self.name)

        tool = ValidTool(my_service=Mock())
        registry.register(tool)

        assert "valid_tool" in registry
        assert registry.get("valid_tool") is tool

    def test_register_tool_missing_dependency_raises(self):
        """Tool missing a required dependency raises ValueError."""
        registry = ToolRegistry()

        class MisconfiguredTool(BaseTool):
            name = "bad_tool"
            description = "A misconfigured tool"
            required_dependencies: ClassVar[list[str]] = ["service_a", "service_b"]

            def __init__(self, service_a):
                # Missing service_b
                self.service_a = service_a

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data=None, tool_name=self.name)

        tool = MisconfiguredTool(service_a=Mock())

        with pytest.raises(ValueError) as exc_info:
            registry.register(tool)

        assert "bad_tool" in str(exc_info.value)
        assert "service_b" in str(exc_info.value)
        assert "missing required dependencies" in str(exc_info.value).lower()

    def test_register_tool_no_dependencies(self):
        """Tool with no required dependencies registers successfully."""
        registry = ToolRegistry()

        class NoDepsTools(BaseTool):
            name = "no_deps"
            description = "No dependencies"
            required_dependencies: ClassVar[list[str]] = []

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data=None, tool_name=self.name)

        tool = NoDepsTools()
        registry.register(tool)

        assert "no_deps" in registry

    def test_register_duplicate_tool_raises(self):
        """Registering a tool with the same name raises ValueError."""
        registry = ToolRegistry()

        class DummyTool(BaseTool):
            name = "duplicate"
            description = "First tool"
            required_dependencies: ClassVar[list[str]] = []

            @property
            def parameters_schema(self) -> dict:
                return {"type": "object", "properties": {}}

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data=None, tool_name=self.name)

        registry.register(DummyTool())

        with pytest.raises(ValueError) as exc_info:
            registry.register(DummyTool())

        assert "already registered" in str(exc_info.value)
