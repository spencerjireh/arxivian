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
    # Multi-tool scenarios
    RouterScenario(
        id="multi_tool_search_and_list",
        query="Search arxiv for recent transformer papers and list what I've ingested",
        expected_tools=["arxiv_search", "list_papers"],
        expected_action="execute_tools",
        description="Two distinct requests: arxiv search + list ingested papers",
    ),
    RouterScenario(
        id="multi_tool_retrieve_and_arxiv",
        query="Retrieve what we have on BERT and search arxiv for newer papers",
        expected_tools=["retrieve_chunks", "arxiv_search"],
        expected_action="execute_tools",
        description="Retrieve from knowledge base + search arxiv externally",
    ),
    RouterScenario(
        id="multi_tool_list_and_citations",
        query="List our papers and show citations for 1706.03762",
        expected_tools=["list_papers", "explore_citations"],
        expected_action="execute_tools",
        description="List ingested papers + explore citations for a specific paper",
    ),
    # History-aware scenarios
    RouterScenario(
        id="history_arxiv_after_retrieval",
        query="Now search arxiv for more on this topic",
        conversation_history=[
            {"role": "user", "content": "Retrieve from our knowledge base what we have on attention mechanisms"},
            {
                "role": "assistant",
                "content": (
                    "Based on our knowledge base, the Transformer architecture relies "
                    "on multi-head self-attention mechanisms."
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="retrieve_chunks",
                tool_args={"query": "attention mechanisms"},
                success=True,
                result_summary="Retrieved 3 items",
            ),
        ],
        expected_tools=["arxiv_search"],
        expected_action="execute_tools",
        description="After retrieval, user asks to search arxiv for more -- context from history",
    ),
    RouterScenario(
        id="history_citations_after_discussion",
        query="Show the citation graph for paper 1706.03762 we just discussed",
        conversation_history=[
            {"role": "user", "content": "Tell me about paper 1706.03762"},
            {
                "role": "assistant",
                "content": (
                    "Paper 1706.03762 is 'Attention Is All You Need' by Vaswani et al. "
                    "It introduces the Transformer architecture."
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="retrieve_chunks",
                tool_args={"query": "paper 1706.03762"},
                success=True,
                result_summary="Retrieved 3 items",
            ),
        ],
        expected_tools=["explore_citations"],
        expected_action="execute_tools",
        description="Follow-up asking for citations of previously discussed paper",
    ),
    RouterScenario(
        id="history_retrieve_followup",
        query="Retrieve more from our knowledge base about Transformer training procedures and datasets",
        conversation_history=[
            {"role": "user", "content": "Retrieve what our knowledge base has on the Transformer"},
            {
                "role": "assistant",
                "content": (
                    "The Transformer is an architecture that relies entirely on attention "
                    "mechanisms, dispensing with recurrence and convolutions."
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="retrieve_chunks",
                tool_args={"query": "Transformer"},
                success=True,
                result_summary="Retrieved 3 items",
            ),
        ],
        expected_tools=["retrieve_chunks"],
        expected_action="execute_tools",
        description="Explicit retrieval follow-up asking for more details on training",
    ),
]
