"""Router evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.conversation import ConversationMessage
from src.schemas.langgraph_state import ToolExecution


@dataclass
class RouterScenario:
    id: str
    query: str
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    available_chunks: list[dict] = field(default_factory=list)
    tool_history: list[ToolExecution] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    expected_action: str = "execute_tools"
    description: str = ""


ROUTER_SCENARIOS: list[RouterScenario] = [
    RouterScenario(
        id="fresh_paper_question",
        query="Search our knowledge base for what the Attention Is All You Need paper says about multi-head attention",
        expected_tools=["retrieve_chunks"],
        expected_action="execute_tools",
        description="Explicit retrieval request should trigger retrieve_chunks",
    ),
    RouterScenario(
        id="arxiv_search",
        query="Find papers on arXiv about reinforcement learning from human feedback",
        expected_tools=["arxiv_search"],
        expected_action="execute_tools",
        description="Explicit search request should trigger arxiv_search",
    ),
    RouterScenario(
        id="list_papers",
        query="What papers do we have about transformers?",
        expected_tools=["list_papers"],
        expected_action="execute_tools",
        description="Inventory question should trigger list_papers",
    ),
    RouterScenario(
        id="generate_with_context",
        query="Can you summarize what we just discussed?",
        conversation_history=[
            {"role": "user", "content": "What is BERT?"},
            {
                "role": "assistant",
                "content": (
                    "BERT is a language model that uses bidirectional pre-training "
                    "on masked language modeling and next sentence prediction tasks."
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="retrieve_chunks",
                tool_args={"query": "What is BERT?"},
                success=True,
                result_summary="Retrieved 6 items",
            ),
        ],
        expected_tools=[],
        expected_action="generate",
        description="Follow-up with sufficient context should generate directly",
    ),
    RouterScenario(
        id="explore_citations",
        query="Show the citation graph for paper 1706.03762 which is already in our knowledge base",
        expected_tools=["explore_citations"],
        expected_action="execute_tools",
        description="Citation query for ingested paper should trigger explore_citations",
    ),
]
