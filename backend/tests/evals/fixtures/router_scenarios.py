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
    # History-aware scenarios
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
    # Anti-escalation: weak retrieve should generate, not re-run retrieval
    RouterScenario(
        id="no_escalation_after_weak_retrieve",
        query="What does the paper say about dropout regularization?",
        tool_history=[
            ToolExecution(
                tool_name="retrieve_chunks",
                tool_args={"query": "dropout regularization"},
                success=True,
                result_summary="Retrieved 1 item (low relevance)",
            ),
        ],
        expected_tools=[],
        expected_action="generate",
        description=(
            "After retrieve_chunks returned weak results, the router should generate "
            "with available context rather than re-running retrieval"
        ),
    ),
    # Content questions default to retrieve_chunks without explicit "retrieve" language
    RouterScenario(
        id="content_question_defaults_retrieve",
        query="Summarize the attention mechanism from the Transformer paper",
        expected_tools=["retrieve_chunks"],
        expected_action="execute_tools",
        description=(
            "A content question about a research topic should default to "
            "retrieve_chunks even without explicit retrieval language"
        ),
    ),
    # Implicit intent scenarios -- no directive verbs
    RouterScenario(
        id="implicit_retrieve_conceptual",
        query="How does positional encoding work in the Transformer?",
        expected_tools=["retrieve_chunks"],
        expected_action="execute_tools",
        description="Conceptual question should infer retrieve_chunks without directive verbs",
    ),
    RouterScenario(
        id="implicit_citations",
        query="What are the academic influences on 1706.03762?",
        expected_tools=["explore_citations"],
        expected_action="execute_tools",
        description="Question about academic influences should infer explore_citations",
    ),
    RouterScenario(
        id="implicit_retrieve_comparison",
        query=("What are the key differences between how BERT and GPT-3 approach pre-training?"),
        expected_tools=["retrieve_chunks"],
        expected_action="execute_tools",
        description="Comparative question should infer retrieve_chunks",
    ),
]
