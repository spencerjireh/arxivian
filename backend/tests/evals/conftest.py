"""Eval test configuration -- real LLM, mocked external services."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import litellm
import pytest

from src.clients.litellm_client import LiteLLMClient
from src.services.agent_service.context import AgentContext, ConversationFormatter
from src.services.agent_service.graph_builder import get_compiled_graph
from src.services.agent_service.tools import (
    ToolRegistry,
    RetrieveChunksTool,
    IngestPapersTool,
    ListPapersTool,
    ArxivSearchTool,
    ExploreCitationsTool,
    SummarizePaperTool,
)


def pytest_collection_modifyitems(items: list) -> None:
    """Auto-apply eval marker to all tests in this directory."""
    evals_dir = os.path.dirname(__file__)
    for item in items:
        if str(item.fspath).startswith(evals_dir):
            item.add_marker(pytest.mark.eval)


# ---------------------------------------------------------------------------
# Session-scoped: real LLM client + compiled graph
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _configure_litellm() -> None:
    """Drop unsupported params (e.g. temperature) for reasoning models."""
    litellm.drop_params = True


@pytest.fixture(scope="session")
def real_llm_client() -> LiteLLMClient:
    model = os.environ.get("EVAL_LLM_MODEL", "nvidia_nim/openai/gpt-oss-120b")
    return LiteLLMClient(model=model, timeout=120.0)


@pytest.fixture(scope="session")
def compiled_graph():
    get_compiled_graph.cache_clear()
    return get_compiled_graph()


# ---------------------------------------------------------------------------
# Function-scoped: mocked external services
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_search_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ingest_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_arxiv_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_paper_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def eval_context(
    real_llm_client: LiteLLMClient,
    mock_search_service: AsyncMock,
    mock_ingest_service: AsyncMock,
    mock_arxiv_client: AsyncMock,
    mock_paper_repository: AsyncMock,
) -> AgentContext:
    """Real LLM + mocked services. Registers all tools so the router sees full schemas."""
    registry = ToolRegistry()
    registry.register(
        RetrieveChunksTool(search_service=mock_search_service, default_top_k=6)
    )
    registry.register(IngestPapersTool(ingest_service=mock_ingest_service))
    registry.register(ListPapersTool(ingest_service=mock_ingest_service))
    registry.register(ArxivSearchTool(arxiv_client=mock_arxiv_client))
    registry.register(ExploreCitationsTool(paper_repository=mock_paper_repository))
    registry.register(
        SummarizePaperTool(paper_repository=mock_paper_repository, llm_client=real_llm_client)
    )

    return AgentContext(
        llm_client=real_llm_client,
        search_service=mock_search_service,
        ingest_service=mock_ingest_service,
        arxiv_client=mock_arxiv_client,
        paper_repository=mock_paper_repository,
        tool_registry=registry,
        conversation_formatter=ConversationFormatter(max_turns=5),
        guardrail_threshold=75,
        top_k=1,  # accept a single relevant chunk to avoid rewrite loops
        max_retrieval_attempts=1,
        max_iterations=2,  # limit graph loops (each makes several slow LLM calls)
        temperature=1,  # reasoning models only support temperature=1
        max_generation_tokens=16000,  # reasoning models use tokens for CoT
    )


@pytest.fixture
def eval_config(eval_context: AgentContext) -> dict:
    return {"configurable": {"context": eval_context}}


# ---------------------------------------------------------------------------
# Autouse: patch adispatch_custom_event (no streaming callback in ainvoke)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_custom_events():
    with (
        patch(
            "src.services.agent_service.nodes.executor.adispatch_custom_event",
            new_callable=AsyncMock,
        ),
        patch(
            "src.services.agent_service.nodes.generation.adispatch_custom_event",
            new_callable=AsyncMock,
        ),
        patch(
            "src.services.agent_service.nodes.out_of_scope.adispatch_custom_event",
            new_callable=AsyncMock,
        ),
    ):
        yield
