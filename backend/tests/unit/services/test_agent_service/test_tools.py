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
    async def test_empty_query_returns_error(self, tool):
        result = await tool.execute(query="")
        assert result.success is False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_error(self, tool):
        result = await tool.execute(query="   ")
        assert result.success is False
        assert "required" in result.error.lower()

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

    @pytest.mark.asyncio
    async def test_zero_results_with_date_filter_includes_message(self, tool, mock_arxiv_client):
        mock_arxiv_client.search_papers.return_value = []

        result = await tool.execute(
            query="machine learning", start_date="2026-02-14", end_date="2026-02-14"
        )

        assert result.success is True
        assert result.data["count"] == 0
        assert "message" in result.data
        assert "no papers matched" in result.data["message"].lower()

    @pytest.mark.asyncio
    async def test_zero_results_without_date_filter_no_message(self, tool, mock_arxiv_client):
        mock_arxiv_client.search_papers.return_value = []

        result = await tool.execute(query="machine learning")

        assert result.success is True
        assert result.data["count"] == 0
        assert "message" not in result.data

    def test_class_variables(self, tool):
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
        assert tool.extends_chunks is False
        assert "paper_repository" in tool.required_dependencies
        assert "llm_client" in tool.required_dependencies


class TestArxivSearchPromptText:
    """Tests for arxiv_search prompt text formatting."""

    def test_formats_papers_with_all_fields(self):
        from src.services.agent_service.tools.arxiv_search import _format_search_results

        data = {
            "count": 2,
            "papers": [
                {
                    "arxiv_id": "2602.12259",
                    "title": "Think like a Scientist",
                    "authors": ["J. Yang", "O. Venkatachalam", "A. Smith", "B. Jones"],
                    "abstract": "A " * 100,  # 200 chars
                    "categories": ["cs.AI", "cs.LG"],
                    "published_date": "2026-02-12T00:00:00",
                    "pdf_url": "https://arxiv.org/pdf/2602.12259",
                },
                {
                    "arxiv_id": "2602.11111",
                    "title": "Short Paper",
                    "authors": ["Solo Author"],
                    "abstract": "Brief.",
                    "categories": ["cs.CL"],
                    "published_date": "2026-02-10T00:00:00",
                },
            ],
        }
        result = _format_search_results(data)

        assert result.startswith("Found 2 papers:")
        assert '"Think like a Scientist" by J. Yang, O. Venkatachalam, A. Smith et al.' in result
        assert "ID: 2602.12259" in result
        assert "Feb 12, 2026" in result
        assert "cs.AI, cs.LG" in result
        # Abstract truncated to 150 chars
        assert "..." in result
        # pdf_url should NOT appear
        assert "pdf" not in result.lower()
        # Second paper
        assert '"Short Paper" by Solo Author' in result
        assert "Brief." in result

    def test_no_papers_returns_message(self):
        from src.services.agent_service.tools.arxiv_search import _format_search_results

        assert _format_search_results({"count": 0, "papers": []}) == "No papers found."

    def test_no_papers_with_message_returns_that_message(self):
        from src.services.agent_service.tools.arxiv_search import _format_search_results

        data = {
            "count": 0,
            "papers": [],
            "message": "No papers matched the given date range.",
        }
        assert _format_search_results(data) == "No papers matched the given date range."

    def test_missing_fields_handled_gracefully(self):
        from src.services.agent_service.tools.arxiv_search import _format_search_results

        result = _format_search_results({"count": 1, "papers": [{"title": "Minimal"}]})
        assert '"Minimal" by Unknown' in result


class TestListPapersPromptText:
    """Tests for list_papers prompt text formatting."""

    def test_formats_knowledge_base_papers(self):
        from src.services.agent_service.tools.list_papers import _format_list_results

        data = {
            "total_count": 25,
            "returned": 2,
            "papers": [
                {
                    "arxiv_id": "1706.03762",
                    "title": "Attention Is All You Need",
                    "authors": ["A. Vaswani", "N. Shazeer"],
                    "abstract": "The dominant sequence models...",
                    "categories": ["cs.CL"],
                    "published_date": "2017-06-12T00:00:00",
                },
                {
                    "arxiv_id": "1810.04805",
                    "title": "BERT",
                    "authors": ["J. Devlin"],
                    "abstract": "We introduce BERT.",
                    "categories": ["cs.CL"],
                    "published_date": "2018-10-11T00:00:00",
                },
            ],
        }
        result = _format_list_results(data)

        assert result.startswith("Knowledge base: 25 papers (showing 2):")
        assert "Attention Is All You Need" in result
        assert "BERT" in result

    def test_empty_knowledge_base(self):
        from src.services.agent_service.tools.list_papers import _format_list_results

        assert (
            _format_list_results({"total_count": 0, "returned": 0, "papers": []})
            == "No papers in knowledge base."
        )


class TestIngestPromptText:
    """Tests for ingest prompt text formatting."""

    def test_formats_ingestion_summary(self):
        from src.services.agent_service.tools.ingest import _format_ingest_summary

        data = {
            "status": "completed",
            "papers_fetched": 2,
            "papers_processed": 2,
            "chunks_created": 30,
            "duration_seconds": 5.12,
            "papers": [
                {"arxiv_id": "1706.03762", "title": "Attention Is All You Need", "chunks": 15},
                {"arxiv_id": "1810.04805", "title": "BERT", "chunks": 15},
            ],
            "errors": [],
        }
        result = _format_ingest_summary(data)

        assert "Ingested 2 papers (30 chunks total):" in result
        assert '"Attention Is All You Need" [1706.03762] - 15 chunks' in result
        assert '"BERT" [1810.04805] - 15 chunks' in result
        assert "Errors" not in result

    def test_formats_with_errors(self):
        from src.services.agent_service.tools.ingest import _format_ingest_summary

        data = {
            "status": "completed",
            "papers_fetched": 2,
            "papers_processed": 1,
            "chunks_created": 15,
            "duration_seconds": 3.0,
            "papers": [
                {"arxiv_id": "1706.03762", "title": "Attention Is All You Need", "chunks": 15},
            ],
            "errors": [{"arxiv_id": "9999.99999", "error": "PDF download failed"}],
        }
        result = _format_ingest_summary(data)

        assert "Errors (1):" in result
        assert "[9999.99999] PDF download failed" in result


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
