"""Eval test configuration -- real LLM, mocked external services."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import litellm
import pytest

from src.clients.litellm_client import LiteLLMClient
from src.services.agent_service.context import AgentContext, ConversationFormatter, ScopedPaper
from src.services.agent_service.graph_builder import build_graph
from src.services.agent_service.tools import (
    ExploreCitationsTool,
    RetrieveChunksTool,
    SemanticScholarTool,
    ToolRegistry,
)

from .helpers import ServiceMockBuilder, ServiceMocks

# Every eval turn is scoped to this paper (the canned chunks are from it).
EVAL_SCOPE = ScopedPaper(
    paper_id="00000000-0000-0000-0000-000000000001",
    arxiv_id="1706.03762",
    title="Attention Is All You Need",
)


def pytest_collection_modifyitems(items: list) -> None:
    """Auto-apply eval marker to all tests in this directory (except integration/)."""
    evals_dir = str(Path(__file__).parent)
    integration_dir = str(Path(__file__).parent / "integration")
    for item in items:
        fspath = str(item.fspath)
        if fspath.startswith(evals_dir) and not fspath.startswith(integration_dir):
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
    model = os.environ.get("EVAL_LLM_MODEL", "openai/gpt-5-nano")
    return LiteLLMClient(model=model, timeout=120.0)


@pytest.fixture(scope="session")
def compiled_graph():
    return build_graph()


# ---------------------------------------------------------------------------
# Function-scoped: mocked external services
# ---------------------------------------------------------------------------


@pytest.fixture
def service_mocks() -> ServiceMocks:
    return ServiceMockBuilder().build()


@pytest.fixture
def mock_search_service(service_mocks: ServiceMocks) -> AsyncMock:
    return service_mocks.search_service


@pytest.fixture
def mock_paper_repository(service_mocks: ServiceMocks) -> AsyncMock:
    return service_mocks.paper_repository


@pytest.fixture
def eval_context(
    real_llm_client: LiteLLMClient,
    mock_search_service: AsyncMock,
    mock_paper_repository: AsyncMock,
    service_mocks: ServiceMocks,
) -> AgentContext:
    """Real LLM + mocked services, scoped to EVAL_SCOPE like every production turn."""
    registry = ToolRegistry()
    registry.register(
        RetrieveChunksTool(
            search_service=mock_search_service, paper_id=EVAL_SCOPE.paper_id, default_top_k=6
        )
    )
    registry.register(ExploreCitationsTool(paper_repository=mock_paper_repository))
    registry.register(
        SemanticScholarTool(semantic_scholar_client=service_mocks.semantic_scholar_client)
    )

    return AgentContext(
        llm_client=real_llm_client,
        search_service=mock_search_service,
        scoped_paper=EVAL_SCOPE,
        paper_repository=mock_paper_repository,
        tool_registry=registry,
        conversation_formatter=ConversationFormatter(max_turns=5),
        guardrail_threshold=75,
        top_k=1,  # accept a single relevant chunk to avoid rewrite loops
        max_iterations=2,  # limit graph loops (each makes several slow LLM calls)
        temperature=1,  # reasoning models only support temperature=1
        max_generation_tokens=16000,  # reasoning models use tokens for CoT
    )


@pytest.fixture
def eval_config(eval_context: AgentContext) -> dict:
    return {"configurable": {"context": eval_context}}


# ---------------------------------------------------------------------------
# Autouse: stub get_stream_writer (no active stream in ainvoke / direct calls)
# ---------------------------------------------------------------------------

_STREAM_WRITER_TARGETS = (
    "src.services.agent_service.nodes.executor.get_stream_writer",
    "src.services.agent_service.nodes.generation.get_stream_writer",
    "src.services.agent_service.nodes.out_of_scope.get_stream_writer",
)


@pytest.fixture(autouse=True)
def patch_stream_writer():
    """Stub get_stream_writer in every node module that imports it."""
    noop_writer = lambda data: None  # noqa: E731
    patches = [patch(target, return_value=noop_writer) for target in _STREAM_WRITER_TARGETS]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()
