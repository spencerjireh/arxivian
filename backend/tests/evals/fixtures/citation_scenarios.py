"""Citation accuracy evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.conversation import ConversationMessage
from .canned_data import TRANSFORMER_CHUNKS, BERT_CHUNKS


@dataclass
class CitationScenario:
    id: str
    query: str
    canned_chunks: list[dict] = field(default_factory=list)
    expected_arxiv_ids: list[str] = field(default_factory=list)
    expected_titles: list[str] = field(default_factory=list)
    canned_tool_outputs: list[dict] = field(default_factory=list)
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    description: str = ""


CITATION_SCENARIOS: list[CitationScenario] = [
    CitationScenario(
        id="cites_single_source",
        query="Search our knowledge base for how the Transformer uses attention mechanisms",
        canned_chunks=TRANSFORMER_CHUNKS,
        expected_arxiv_ids=["1706.03762"],
        expected_titles=["Attention Is All You Need"],
        description="Single-source answer should cite only 1706.03762",
    ),
    CitationScenario(
        id="cites_multiple_sources",
        query=(
            "Retrieve from our knowledge base a comparison of the Transformer and BERT architectures"
        ),
        canned_chunks=TRANSFORMER_CHUNKS + BERT_CHUNKS,
        expected_arxiv_ids=["1706.03762", "1810.04805"],
        expected_titles=[
            "Attention Is All You Need",
            "BERT: Pre-training of Deep Bidirectional Transformers",
        ],
        description="Multi-source answer should cite both papers",
    ),
    CitationScenario(
        id="no_hallucinated_citations",
        query="Search our knowledge base for what the Transformer paper says about training results",
        canned_chunks=TRANSFORMER_CHUNKS,
        expected_arxiv_ids=["1706.03762"],
        expected_titles=["Attention Is All You Need"],
        description="Should cite only 1706.03762, no fabricated paper references",
    ),
]
