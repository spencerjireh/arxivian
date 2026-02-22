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
            {
                "role": "user",
                "content": "Retrieve from our knowledge base what we have on attention mechanisms",
            },
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
    # Anti-escalation: weak retrieve should generate, not escalate to arxiv_search
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
            "with available context rather than silently escalating to arxiv_search"
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
        id="implicit_arxiv_discovery",
        query=("I wonder what the latest work on diffusion models for text generation looks like"),
        expected_tools=["arxiv_search"],
        expected_action="execute_tools",
        description="Curiosity about recent work should infer arxiv_search",
    ),
    RouterScenario(
        id="implicit_list_inventory",
        query="What do I have available on vision transformers?",
        expected_tools=["list_papers"],
        expected_action="execute_tools",
        description="Inventory question phrased naturally should infer list_papers",
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
    # propose_ingest scenarios
    RouterScenario(
        id="propose_ingest_after_search",
        query="Those look great, please add them to my knowledge base",
        conversation_history=[
            {"role": "user", "content": "Search arXiv for papers on RLHF"},
            {
                "role": "assistant",
                "content": (
                    "I found several papers on RLHF:\n"
                    "1. 'Training language models to follow instructions with human feedback' "
                    "(2203.02155)\n"
                    "2. 'Learning to summarize from human feedback' (2009.01325)"
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="arxiv_search",
                tool_args={"query": "RLHF"},
                success=True,
                result_summary="Found 2 papers",
            ),
        ],
        expected_tools=["propose_ingest"],
        expected_action="execute_tools",
        description="After arxiv_search, explicit add request should trigger propose_ingest",
    ),
    RouterScenario(
        id="propose_ingest_combined",
        query="Find papers about RLHF on arXiv and add the best ones to my collection",
        expected_tools=["arxiv_search"],
        expected_action="execute_tools",
        description=(
            "Combined search+add should route to arxiv_search first; "
            "propose_ingest follows after search completes"
        ),
    ),
    RouterScenario(
        id="no_auto_propose_without_request",
        query="What did the recent search find?",
        conversation_history=[
            {"role": "user", "content": "Search arXiv for papers on RLHF"},
            {
                "role": "assistant",
                "content": (
                    "I found several papers on RLHF:\n"
                    "1. 'Training language models to follow instructions with human feedback' "
                    "(2203.02155)\n"
                    "2. 'Learning to summarize from human feedback' (2009.01325)"
                ),
            },
        ],
        tool_history=[
            ToolExecution(
                tool_name="arxiv_search",
                tool_args={"query": "RLHF"},
                success=True,
                result_summary="Found 2 papers",
            ),
        ],
        expected_tools=[],
        expected_action="generate",
        description="Asking about search results must NOT auto-propose ingestion",
    ),
    # Dedup guard: re-emitting succeeded tool should force direct
    RouterScenario(
        id="dedup_forces_direct_after_arxiv_success",
        query="Thanks, that covers what I needed. Can you restate those results more concisely?",
        tool_history=[
            ToolExecution(
                tool_name="arxiv_search",
                tool_args={"query": "knowledge distillation"},
                success=True,
                result_summary="Found 5 papers",
            ),
        ],
        conversation_history=[
            {"role": "user", "content": "Search arXiv for knowledge distillation papers"},
            {"role": "assistant", "content": "I found 5 papers on knowledge distillation..."},
        ],
        expected_tools=[],
        expected_action="generate",
        description="After arxiv_search succeeded, restatement request should generate from context, not re-search",
    ),
    # Dedup guard preserves novel tools when chaining
    RouterScenario(
        id="dedup_preserves_ingest_after_search",
        query="Great, add those papers to my library",
        tool_history=[
            ToolExecution(
                tool_name="arxiv_search",
                tool_args={"query": "knowledge distillation"},
                success=True,
                result_summary="Found 5 papers",
            ),
        ],
        conversation_history=[
            {"role": "user", "content": "Search arXiv for knowledge distillation papers"},
            {"role": "assistant", "content": "I found 5 papers on knowledge distillation..."},
        ],
        expected_tools=["propose_ingest"],
        expected_action="execute_tools",
        description=(
            "After arxiv_search succeeded, explicit ingest request should "
            "propose_ingest (not re-search)"
        ),
    ),
    # Date-aware routing
    RouterScenario(
        id="arxiv_search_with_date",
        query="Find papers about transformers published in February 2026",
        expected_tools=["arxiv_search"],
        expected_action="execute_tools",
        description="Query with date filter should route to arxiv_search",
    ),
]
