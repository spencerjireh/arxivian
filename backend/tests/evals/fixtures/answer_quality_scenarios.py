"""Answer quality evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.conversation import ConversationMessage
from .canned_data import (
    TRANSFORMER_CHUNKS,
    BERT_CHUNKS,
    IRRELEVANT_CHUNKS,
    ARXIV_SEARCH_RESULTS,
)


@dataclass
class AnswerQualityScenario:
    id: str
    query: str
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    canned_chunks: list[dict] = field(default_factory=list)
    canned_tool_outputs: list[dict] = field(default_factory=list)
    description: str = ""


ANSWER_QUALITY_SCENARIOS: list[AnswerQualityScenario] = [
    AnswerQualityScenario(
        id="factual_with_good_chunks",
        query="Search our knowledge base for how multi-head attention works in the Transformer",
        canned_chunks=TRANSFORMER_CHUNKS,
        description="Factual question with highly relevant chunks",
    ),
    AnswerQualityScenario(
        id="no_relevant_chunks",
        query="Retrieve papers from our knowledge base about quantum error correction",
        canned_chunks=IRRELEVANT_CHUNKS,
        description="Question with no relevant chunks -- should caveat honestly",
    ),
    AnswerQualityScenario(
        id="synthesis_across_chunks",
        query="Retrieve and compare the architectures of BERT and the original Transformer from our ingested papers",
        canned_chunks=TRANSFORMER_CHUNKS + BERT_CHUNKS,
        description="Synthesis question requiring information from multiple papers",
    ),
    AnswerQualityScenario(
        id="arxiv_search_outputs",
        query="Search arXiv for papers about attention mechanisms in NLP",
        canned_chunks=[],
        canned_tool_outputs=[{"tool_name": "arxiv_search", "data": ARXIV_SEARCH_RESULTS}],
        description="Question answered via arxiv_search tool outputs",
    ),
    AnswerQualityScenario(
        id="partial_relevance",
        query="Retrieve from our knowledge base the training results and datasets for the Transformer model",
        canned_chunks=TRANSFORMER_CHUNKS[1:2] + IRRELEVANT_CHUNKS,
        description="Mix of relevant and irrelevant chunks -- grading integration",
    ),
]
