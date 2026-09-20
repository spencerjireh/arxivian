"""Tests for paper-scoped chat: scoped retrieval, tool registry, prompts."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.services.agent_service.context import AgentContext, ScopedPaper
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
    async def test_uses_within_paper_retrieval_without_rrf_filter(self):
        search = AsyncMock()
        search.retrieve_within_paper.return_value = [_result(0.9), _result(0.2)]
        tool = RetrieveChunksTool(search_service=search, paper_id=SCOPE.paper_id, default_top_k=6)

        result = await tool.execute(query="what is the method?")

        search.retrieve_within_paper.assert_awaited_once_with(
            query="what is the method?", paper_id=SCOPE.paper_id, top_k=6, min_score=0.0
        )
        search.hybrid_search.assert_not_called()
        assert result.success is True
        assert len(result.data) == 2  # cosine scores are not filtered by the RRF threshold
        assert "currently viewing" in tool.description

    async def test_empty_query_rejected(self):
        tool = RetrieveChunksTool(search_service=AsyncMock(), paper_id=SCOPE.paper_id)
        result = await tool.execute(query="  ")
        assert result.success is False


@pytest.mark.unit
class TestScopedRegistry:
    def _context(self) -> AgentContext:
        return AgentContext(
            llm_client=Mock(),
            search_service=AsyncMock(),
            scoped_paper=SCOPE,
            semantic_scholar_client=Mock(),
            paper_repository=Mock(),
        )

    def test_registry_has_only_scoped_tools(self):
        names = {t.name for t in self._context().tool_registry}
        assert names == {"retrieve_chunks", "explore_citations", "semantic_scholar"}

    def test_retrieve_tool_carries_paper_id(self):
        tool = self._context().tool_registry.get("retrieve_chunks")
        assert tool.paper_id == SCOPE.paper_id

    def test_optional_clients_omitted(self):
        ctx = AgentContext(llm_client=Mock(), search_service=AsyncMock(), scoped_paper=SCOPE)
        assert {t.name for t in ctx.tool_registry} == {"retrieve_chunks"}


@pytest.mark.unit
class TestScopedPrompts:
    def test_scope_note_in_user_prompt(self):
        note = scoped_paper_note("2301.00001", "Attention")
        _, user = get_classify_and_route_prompt(
            query="explain the method", tool_schemas=[], scope_note=note
        )
        assert "[SCOPE] This conversation is scoped to paper 2301.00001 ('Attention')" in user

    def test_no_note_by_default(self):
        _, user = get_classify_and_route_prompt(query="q", tool_schemas=[])
        assert "[SCOPE]" not in user
