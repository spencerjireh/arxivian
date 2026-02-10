"""Seed paper IDs and test scenarios for integration evals."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Seed papers (ingested once via `just inteval-seed`)
# ---------------------------------------------------------------------------

SEED_PAPERS: list[str] = [
    "1706.03762",  # Attention Is All You Need
    "1810.04805",  # BERT: Pre-training of Deep Bidirectional Transformers
    "2005.14165",  # Language Models are Few-Shot Learners (GPT-3)
    "2010.11929",  # An Image is Worth 16x16 Words (ViT)
    # NOTE: 2303.08774 (GPT-4) excluded -- PDF contains null bytes that
    # PostgreSQL rejects (CharacterNotInRepertoireError: 0x00).
]


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


RETRIEVAL_SCENARIOS: list[IntegrationScenario] = [
    IntegrationScenario(
        id="transformer_architecture",
        query="Based on the papers in the knowledge base, explain the multi-head attention mechanism described in the Transformer paper.",
        description="Should retrieve Attention Is All You Need and mention key concepts.",
        expected_source_ids=["1706.03762"],
        expected_keywords=["attention"],
    ),
    IntegrationScenario(
        id="bert_pretraining",
        query="Using the ingested papers, explain how BERT uses masked language modeling during pre-training.",
        description="Should retrieve BERT paper and discuss masked LM.",
        expected_source_ids=["1810.04805"],
        expected_keywords=["mask"],
    ),
    IntegrationScenario(
        id="gpt3_few_shot",
        query="Retrieve information from the papers about few-shot learning in GPT-3. How does model scaling affect few-shot performance?",
        description="Should retrieve GPT-3 paper and discuss few-shot / scaling.",
        expected_source_ids=["2005.14165"],
        expected_keywords=["few-shot"],
    ),
    IntegrationScenario(
        id="gpt3_scaling",
        query="Search the knowledge base for information about how GPT-3 demonstrates that scaling up language models improves performance.",
        description="Should retrieve GPT-3 paper and discuss scaling laws.",
        expected_source_ids=["2005.14165"],
        expected_keywords=["scal"],
    ),
    IntegrationScenario(
        id="vision_transformer",
        query="Retrieve the relevant chunks from the knowledge base about how the Vision Transformer (ViT) paper applies transformers to image classification using patch embeddings.",
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


MULTI_TURN_SCENARIOS: list[MultiTurnScenario] = [
    MultiTurnScenario(
        id="transformer_followup",
        description="Ask about transformers from papers, then follow up on a detail.",
        turns=[
            "Using the ingested papers, explain what the Transformer architecture is and what problem it solves.",
            "Based on the same paper, can you elaborate on how positional encoding works?",
        ],
        expected_source_ids=["1706.03762"],
    ),
    MultiTurnScenario(
        id="cross_paper_comparison",
        description="Ask about BERT from papers, then compare with GPT-3.",
        turns=[
            "Retrieve information about how BERT's pre-training approach works from the papers.",
            "Based on the papers, how does GPT-3's approach differ from BERT's pre-training?",
        ],
        expected_source_ids=["1810.04805", "2005.14165"],
    ),
]
