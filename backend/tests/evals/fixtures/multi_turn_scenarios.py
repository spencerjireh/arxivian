"""Multi-turn conversation evaluation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from .canned_data import TRANSFORMER_CHUNKS, BERT_CHUNKS


@dataclass
class Turn:
    query: str
    canned_chunks: list[dict] = field(default_factory=list)


@dataclass
class MultiTurnScenario:
    id: str
    turns: list[Turn] = field(default_factory=list)
    description: str = ""


MULTI_TURN_SCENARIOS: list[MultiTurnScenario] = [
    MultiTurnScenario(
        id="initial_then_followup",
        turns=[
            Turn(
                query="Retrieve from our knowledge base what the Transformer architecture is",
                canned_chunks=TRANSFORMER_CHUNKS,
            ),
            Turn(
                query="Retrieve more details about how it handles position information",
                canned_chunks=TRANSFORMER_CHUNKS,
            ),
        ],
        description="Initial question then a follow-up asking for more detail",
    ),
    MultiTurnScenario(
        id="progressive_refinement",
        turns=[
            Turn(
                query="Search our knowledge base for pre-training methods used in modern NLP",
                canned_chunks=BERT_CHUNKS,
            ),
            Turn(
                query="Retrieve more details about how BERT's masked language modeling works",
                canned_chunks=BERT_CHUNKS,
            ),
            Turn(
                query="Retrieve and compare this to the original Transformer training approach",
                canned_chunks=TRANSFORMER_CHUNKS + BERT_CHUNKS,
            ),
        ],
        description="Three turns progressively refining the topic",
    ),
    MultiTurnScenario(
        id="topic_switch",
        turns=[
            Turn(
                query="Retrieve from our knowledge base an explanation of self-attention in the Transformer",
                canned_chunks=TRANSFORMER_CHUNKS,
            ),
            Turn(
                query="Now retrieve information about BERT's pre-training approach from our papers",
                canned_chunks=BERT_CHUNKS,
            ),
        ],
        description="Topic switch between two related but distinct papers",
    ),
]
