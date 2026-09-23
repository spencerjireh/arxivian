"""Seed paper IDs and test scenarios for integration evals."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..fixtures.scoring_scenarios import SCORING_SCENARIOS

# ---------------------------------------------------------------------------
# Seed papers (ingested once via `just inteval-seed`)
# ---------------------------------------------------------------------------

# arXiv IDs whose PDFs break ingestion -- kept out of seeding so the batch does not abort.
UNINGESTABLE: frozenset[str] = frozenset(
    {
        # GPT-4 report -- PDF contains null bytes PostgreSQL rejects
        # (CharacterNotInRepertoireError: 0x00). Its scoring scenario is skipped.
        "2303.08774",
    }
)

# Papers backing the agent retrieval / multi-turn scenarios below.
_RETRIEVAL_SEED: list[str] = [
    "1706.03762",  # Attention Is All You Need
    "1810.04805",  # BERT: Pre-training of Deep Bidirectional Transformers
    "2005.14165",  # Language Models are Few-Shot Learners (GPT-3)
    "2010.11929",  # An Image is Worth 16x16 Words (ViT)
]

# The scoring golden set (ARX-8): every labeled paper except the uningestable ones. The
# scoring eval scores whatever seeded successfully; a missing paper skips its scenario.
_SCORING_SEED: list[str] = [s.arxiv_id for s in SCORING_SCENARIOS if s.arxiv_id not in UNINGESTABLE]

# Deduped, order-stable union.
SEED_PAPERS: list[str] = list(dict.fromkeys([*_RETRIEVAL_SEED, *_SCORING_SEED]))


# ---------------------------------------------------------------------------
# Single-turn retrieval scenarios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegrationScenario:
    id: str
    query: str
    description: str
    expected_source_ids: list[str]
    expected_keywords: list[str]

    @property
    def arxiv_id(self) -> str:
        """The paper the conversation is scoped to."""
        return self.expected_source_ids[0]


RETRIEVAL_SCENARIOS: list[IntegrationScenario] = [
    IntegrationScenario(
        id="transformer_architecture",
        query="Explain the multi-head attention mechanism described in this paper.",
        description="Should retrieve Attention Is All You Need and mention key concepts.",
        expected_source_ids=["1706.03762"],
        expected_keywords=["attention"],
    ),
    IntegrationScenario(
        id="bert_pretraining",
        query="Explain how this paper uses masked language modeling during pre-training.",
        description="Should retrieve BERT paper and discuss masked LM.",
        expected_source_ids=["1810.04805"],
        expected_keywords=["mask"],
    ),
    IntegrationScenario(
        id="gpt3_few_shot",
        query="How does model scaling affect few-shot performance in this paper?",
        description="Should retrieve GPT-3 paper and discuss few-shot / scaling.",
        expected_source_ids=["2005.14165"],
        expected_keywords=["few-shot"],
    ),
    IntegrationScenario(
        id="gpt3_scaling",
        query="How does this paper demonstrate that scaling up language models improves performance?",
        description="Should retrieve GPT-3 paper and discuss scaling laws.",
        expected_source_ids=["2005.14165"],
        expected_keywords=["scal"],
    ),
    IntegrationScenario(
        id="vision_transformer",
        query="How does this paper apply transformers to image classification using patch embeddings?",
        description="Should retrieve ViT paper and discuss patch embedding.",
        expected_source_ids=["2010.11929"],
        expected_keywords=["patch"],
    ),
]


# ---------------------------------------------------------------------------
# Multi-turn conversation scenarios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiTurnScenario:
    id: str
    description: str
    turns: list[str]
    expected_source_ids: list[str] = field(default_factory=list)

    @property
    def arxiv_id(self) -> str:
        return self.expected_source_ids[0]


MULTI_TURN_SCENARIOS: list[MultiTurnScenario] = [
    MultiTurnScenario(
        id="transformer_followup",
        description="Ask about transformers from papers, then follow up on a detail.",
        turns=[
            "Explain what the Transformer architecture is and what problem it solves.",
            "Can you elaborate on how positional encoding works?",
        ],
        expected_source_ids=["1706.03762"],
    ),
    MultiTurnScenario(
        id="bert_followup",
        description="Ask about BERT's pre-training, then follow up on fine-tuning.",
        turns=[
            "How does this paper's pre-training approach work?",
            "And how is the pre-trained model fine-tuned for downstream tasks?",
        ],
        expected_source_ids=["1810.04805"],
    ),
]
