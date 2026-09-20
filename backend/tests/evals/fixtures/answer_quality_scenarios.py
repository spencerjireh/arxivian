"""Answer quality evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.schemas.conversation import ConversationMessage

from .canned_data import (
    BERT_CHUNKS,
    CONTRADICTORY_CHUNKS,
    IRRELEVANT_CHUNKS,
    TRANSFORMER_CHUNKS,
)


@dataclass
class AnswerQualityScenario:
    id: str
    query: str
    conversation_history: list[ConversationMessage] = field(default_factory=list)
    canned_chunks: list[dict] = field(default_factory=list)
    canned_tool_outputs: list[dict] = field(default_factory=list)
    description: str = ""
    metrics_override: list[str] | None = None


ANSWER_QUALITY_SCENARIOS: list[AnswerQualityScenario] = [
    AnswerQualityScenario(
        id="factual_with_good_chunks",
        query="Search our knowledge base for how multi-head attention works in the Transformer",
        canned_chunks=TRANSFORMER_CHUNKS,
        description="Factual question with highly relevant chunks",
        metrics_override=["answer_relevancy", "faithfulness"],
    ),
    AnswerQualityScenario(
        id="no_relevant_chunks",
        query="Retrieve papers from our knowledge base about quantum error correction",
        canned_chunks=IRRELEVANT_CHUNKS,
        description="Question with no relevant chunks -- should caveat honestly",
        metrics_override=["answer_relevancy"],
    ),
    AnswerQualityScenario(
        id="synthesis_across_chunks",
        query="Retrieve and compare the architectures of BERT and the original Transformer from our ingested papers",
        canned_chunks=TRANSFORMER_CHUNKS + BERT_CHUNKS,
        description="Synthesis question requiring information from multiple papers",
        metrics_override=["answer_relevancy", "faithfulness"],
    ),
    AnswerQualityScenario(
        id="partial_relevance",
        query="Retrieve from our knowledge base the training results and datasets for the Transformer model",
        canned_chunks=TRANSFORMER_CHUNKS[1:2] + IRRELEVANT_CHUNKS,
        description="Mix of relevant and irrelevant chunks -- grading integration",
    ),
    # Adversarial / regression scenarios
    AnswerQualityScenario(
        id="contradictory_chunks",
        query="What batch size was used to train the Transformer model?",
        canned_chunks=CONTRADICTORY_CHUNKS,
        description=(
            "Two chunks from the same paper disagree on batch size. "
            "Answer should acknowledge the discrepancy, not silently pick one."
        ),
        metrics_override=["answer_relevancy", "contextual_relevancy"],
    ),
]
