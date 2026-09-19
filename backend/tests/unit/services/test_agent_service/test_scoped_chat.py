"""Tests for paper-scoped chat (SPE-277): scoped retrieval, tool registry, prompts."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.services.agent_service.context import CORPUS_ONLY_TOOLS, AgentContext, ScopedPaper
from src.services.agent_service.prompts import get_classify_and_route_prompt, scoped_paper_note
from src.services.agent_service.tools import RetrieveChunksTool

SCOPE = ScopedPaper(
    paper_id="11111111-1111-1111-1111-111111111111", arxiv_id="2301.00001", title="T"
)


def _result(score: float) -> Mock:
    r = Mock()
    r.chunk_id = "c"
    r.chunk_text = "text"
    r.arxiv_id = "2301.00001"
    r.title = "Paper"
    r.authors = []
    r.section_name = "Intro"
    r.score = score
    r.pdf_url = "https://arxiv.org/pdf/2301.00001.pdf"
    r.published_date = "2023-01-01"
    return r


@pytest.mark.unit
class TestScopedRetrieve:
    async def test_scoped_tool_uses_within_paper_retrieval_without_rrf_filter(self):
        search = AsyncMock()
        search.retrieve_within_paper.return_value = [_result(0.9), _result(0.2)]
        tool = RetrieveChunksTool(search_service=search, default_top_k=6, paper_id=SCOPE.paper_id)

        result = await tool.execute(query="what is the method?")

        search.retrieve_within_paper.assert_awaited_once_with(
            query="what is the method?", paper_id=SCOPE.paper_id, top_k=6, min_score=0.0
        )
        search.hybrid_search.assert_not_called()
        assert result.success is True
        assert len(result.data) == 2  # cosine scores are not filtered by the RRF threshold
        assert "currently viewing" in tool.description

    async def test_unscoped_tool_unchanged(self):
        search = AsyncMock()
        search.hybrid_search.return_value = [_result(0.9), _result(0.2)]
        tool = RetrieveChunksTool(search_service=search, default_top_k=6)

        result = await tool.execute(query="q")

        search.hybrid_search.assert_awaited_once()
        search.retrieve_within_paper.assert_not_called()
        assert len(result.data) == 1
        assert "DEFAULT tool for any content question" in tool.description


@pytest.mark.unit
class TestScopedRegistry:
    def _context(self, scoped: ScopedPaper | None) -> AgentContext:
        return AgentContext(
            llm_client=Mock(),
            search_service=AsyncMock(),
            ingest_service=Mock(paper_repository=Mock()),
            arxiv_client=Mock(),
            semantic_scholar_client=Mock(),
            paper_repository=Mock(),
            scoped_paper=scoped,
        )

    def test_scoped_registry_hides_corpus_tools(self):
        names = set(self._context(SCOPE).tool_registry.list_tools())
        assert names == {"retrieve_chunks", "explore_citations", "semantic_scholar"}
        assert not names & CORPUS_ONLY_TOOLS

    def test_unscoped_registry_has_everything(self):
        names = set(self._context(None).tool_registry.list_tools())
        assert names >= {
            "retrieve_chunks",
            "list_papers",
            "propose_ingest",
            "explore_citations",
            "arxiv_search",
            "semantic_scholar",
        }

    def test_scoped_retrieve_tool_carries_paper_id(self):
        tool = self._context(SCOPE).tool_registry.get("retrieve_chunks")
        assert tool.paper_id == SCOPE.paper_id
        assert self._context(None).tool_registry.get("retrieve_chunks").paper_id is None


@pytest.mark.unit
class TestScopedPrompts:
    def test_scope_note_in_user_prompt(self):
        note = scoped_paper_note("2301.00001", "Attention")
        _, user = get_classify_and_route_prompt(
            query="explain the method", tool_schemas=[], scope_note=note
        )
        assert "[SCOPE] This conversation is scoped to paper 2301.00001 ('Attention')" in user
        assert "arxiv_search, list_papers and propose_ingest are unavailable" in user

    def test_no_note_by_default(self):
        _, user = get_classify_and_route_prompt(query="q", tool_schemas=[])
        assert "[SCOPE]" not in user
