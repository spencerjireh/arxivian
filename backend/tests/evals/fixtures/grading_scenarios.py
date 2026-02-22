"""Grading node evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from .canned_data import TRANSFORMER_CHUNKS, BERT_CHUNKS, IRRELEVANT_CHUNKS


@dataclass
class GradingScenario:
    id: str
    query: str
    chunks: list[dict] = field(default_factory=list)
    expected_relevant_ids: list[str] = field(default_factory=list)
    expect_rewrite: bool = False
    iteration: int = 0
    max_iterations: int = 5
    top_k: int = 3
    description: str = ""


GRADING_SCENARIOS: list[GradingScenario] = [
    GradingScenario(
        id="all_relevant",
        query="Explain the Transformer model architecture and positional encoding",
        chunks=[TRANSFORMER_CHUNKS[0], TRANSFORMER_CHUNKS[2]],
        expected_relevant_ids=["chunk-t1", "chunk-t3"],
        expect_rewrite=False,
        top_k=2,
        description="Architecture + positional encoding chunks match query -- all relevant, no rewrite",
    ),
    GradingScenario(
        id="all_irrelevant",
        query="How does multi-head self-attention work in the Transformer architecture?",
        chunks=IRRELEVANT_CHUNKS,
        expected_relevant_ids=[],
        expect_rewrite=True,
        iteration=0,
        max_iterations=5,
        description="Irrelevant image classification chunk -- none relevant, triggers rewrite",
    ),
    GradingScenario(
        id="mixed_relevance",
        query="What is BERT and how does bidirectional pre-training work?",
        chunks=BERT_CHUNKS + IRRELEVANT_CHUNKS,
        expected_relevant_ids=["chunk-b1", "chunk-b2"],
        expect_rewrite=False,
        top_k=2,
        description="Two BERT chunks fully answer the query -- irrelevant chunk doesn't diminish sufficiency",
    ),
    GradingScenario(
        id="rewrite_suppressed_at_max_iter",
        query="How does multi-head self-attention work in the Transformer architecture?",
        chunks=IRRELEVANT_CHUNKS,
        expected_relevant_ids=[],
        expect_rewrite=False,
        iteration=5,
        max_iterations=5,
        description="No relevant chunks but at max iterations -- rewrite suppressed",
    ),
    GradingScenario(
        id="single_relevant_sufficient",
        query="What is BERT and how does it work?",
        chunks=BERT_CHUNKS,
        expected_relevant_ids=["chunk-b1", "chunk-b2"],
        expect_rewrite=False,
        top_k=1,
        description="Both BERT chunks relevant to 'what is BERT / how it works' -- no rewrite needed",
    ),
]
