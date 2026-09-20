"""Tests for agent tools."""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import ClassVar

from src.services.agent_service.tools import (
    BaseTool,
    ToolResult,
    ToolRegistry,
    RetrieveChunksTool,
    ExploreCitationsTool,
    SemanticScholarTool,
)
from src.services.agent_service.tools.retrieve import MAX_TOP_K


class TestRetrieveChunksTool:
    """Tests for RetrieveChunksTool."""

    @pytest.fixture
    def mock_search_service(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_search_service):
        return RetrieveChunksTool(search_service=mock_search_service, paper_id="p1", default_top_k=6)

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
        mock_search_service.retrieve_within_paper.return_value = []

        await tool.execute(query="test", top_k=100)

        call_args = mock_search_service.retrieve_within_paper.call_args
        assert call_args.kwargs["top_k"] == MAX_TOP_K

    @pytest.mark.asyncio
    async def test_top_k_minimum_is_one(self, tool, mock_search_service):
        mock_search_service.retrieve_within_paper.return_value = []

        await tool.execute(query="test", top_k=0)

        call_args = mock_search_service.retrieve_within_paper.call_args
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

        mock_search_service.retrieve_within_paper.return_value = [mock_result]

        result = await tool.execute(query="transformers")

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["arxiv_id"] == "2301.00001"
        assert result.data[0]["authors"] == ["Author One"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, tool, mock_search_service):
        mock_search_service.retrieve_within_paper.side_effect = Exception("Database error")

        result = await tool.execute(query="test")

        assert result.success is False
        assert "Database error" in result.error

    def test_class_variables(self, tool):
        assert tool.extends_chunks is True
        assert "search_service" in tool.required_dependencies

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
        assert tool.extends_chunks is False
        assert "paper_repository" in tool.required_dependencies


class TestExploreCitationsPromptText:
    """Tests for explore_citations prompt text formatting."""

    def test_formats_references(self):
        from src.services.agent_service.tools.explore_citations import _format_citations

        data = {
            "arxiv_id": "1706.03762",
            "title": "Attention Is All You Need",
            "reference_count": 2,
            "references": [
                "Neural Machine Translation by Jointly Learning to Align and Translate",
                "Sequence to Sequence Learning with Neural Networks",
            ],
        }
        result = _format_citations(data)

        assert 'References from "Attention Is All You Need" [1706.03762] (2 citations):' in result
        assert "1. Neural Machine Translation" in result
        assert "2. Sequence to Sequence Learning" in result

    def test_no_references(self):
        from src.services.agent_service.tools.explore_citations import _format_citations

        data = {
            "arxiv_id": "1706.03762",
            "title": "Attention Is All You Need",
            "reference_count": 0,
            "references": [],
        }
        result = _format_citations(data)

        assert "(0 citations):" in result
        assert "No references available." in result


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


class TestSemanticScholarTool:
    """Tests for SemanticScholarTool."""

    @pytest.fixture
    def mock_s2_client(self):
        return AsyncMock()

    @pytest.fixture
    def tool(self, mock_s2_client):
        return SemanticScholarTool(semantic_scholar_client=mock_s2_client)

    @staticmethod
    def _metrics(**overrides):
        from src.clients.semantic_scholar_client import CitationMetrics

        defaults = dict(
            arxiv_id="2301.00001",
            found=True,
            citation_count=120,
            influential_citation_count=15,
            publication_date="2023-01-01",
            citations_per_month=3.5,
            demand_band="HIGH",
        )
        defaults.update(overrides)
        return CitationMetrics(**defaults)

    @pytest.mark.asyncio
    async def test_empty_arxiv_id_returns_error(self, tool):
        result = await tool.execute(arxiv_id="")
        assert result.success is False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_whitespace_arxiv_id_returns_error(self, tool):
        result = await tool.execute(arxiv_id="   ")
        assert result.success is False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_successful_lookup(self, tool, mock_s2_client):
        mock_s2_client.get_citation_metrics.return_value = self._metrics()

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is True
        assert result.data["citation_count"] == 120
        assert result.data["demand_band"] == "HIGH"
        assert "3.5 citations/month" in result.prompt_text

    @pytest.mark.asyncio
    async def test_arxiv_id_is_stripped_before_lookup(self, tool, mock_s2_client):
        mock_s2_client.get_citation_metrics.return_value = self._metrics()

        await tool.execute(arxiv_id="  2301.00001  ")

        call_args = mock_s2_client.get_citation_metrics.call_args
        assert call_args.args[0] == "2301.00001"

    @pytest.mark.asyncio
    async def test_not_found_still_succeeds(self, tool, mock_s2_client):
        mock_s2_client.get_citation_metrics.return_value = self._metrics(
            found=False,
            citation_count=0,
            influential_citation_count=0,
            publication_date=None,
            citations_per_month=0.0,
            demand_band="LOW",
        )

        result = await tool.execute(arxiv_id="2301.99999")

        assert result.success is True
        assert result.data["found"] is False
        assert "No Semantic Scholar record" in result.prompt_text

    @pytest.mark.asyncio
    async def test_client_error_wrapped_in_failed_result(self, tool, mock_s2_client):
        mock_s2_client.get_citation_metrics.side_effect = RuntimeError("boom")

        result = await tool.execute(arxiv_id="2301.00001")

        assert result.success is False
        assert "boom" in result.error

    def test_class_variables(self, tool):
        assert tool.extends_chunks is False
        assert "semantic_scholar_client" in tool.required_dependencies


class TestSemanticScholarPromptText:
    """Tests for semantic_scholar prompt text formatting."""

    def test_formats_found_metrics(self):
        from src.clients.semantic_scholar_client import CitationMetrics
        from src.services.agent_service.tools.semantic_scholar import _format_metrics

        metrics = CitationMetrics(
            arxiv_id="2301.00001",
            found=True,
            citation_count=120,
            influential_citation_count=15,
            publication_date="2023-01-01",
            citations_per_month=3.5,
            demand_band="HIGH",
        )
        result = _format_metrics(metrics)

        assert "arXiv:2301.00001" in result
        assert "120 citations" in result
        assert "15 influential" in result
        assert "demand: HIGH" in result

    def test_formats_not_found(self):
        from src.clients.semantic_scholar_client import CitationMetrics
        from src.services.agent_service.tools.semantic_scholar import _format_metrics

        metrics = CitationMetrics(arxiv_id="2301.99999", found=False)
        result = _format_metrics(metrics)

        assert "No Semantic Scholar record" in result
        assert "2301.99999" in result
