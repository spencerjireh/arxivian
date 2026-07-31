"""Prompt for Stage 1 cheap triage (batched abstract classification).

Stage 1 runs a single coarse keep/drop judgment over a batch of abstracts on the cheap
default model -- it is NOT one of the Stage 2 rubric dimensions in `prompts.py`. The goal is
recall-biased elimination of the obvious non-candidates (surveys, position papers,
non-implementable theory) before any full-text cost, not a precise score. Stage 2 does the
real scoring on the survivors.

Mirrors the `(system_prompt, user_prompt)` builder convention in `prompts.py`. Output is
validated against `TriageBatchResult` by `generate_structured`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

TRIAGE_SYSTEM_PROMPT = """You triage new arXiv papers for an "implementation feed": papers worth turning into \
working software by an individual engineer. You see only title + abstract, so judge coarsely \
and bias toward KEEPING anything plausibly implementable -- a cheap later stage does the \
precise scoring, so a false keep is far cheaper than a false drop.

For each paper return:
- paper_class: one of method | survey | benchmark | theory | position.
- rough_implementability (0-100): a coarse guess at how buildable the core contribution is \
by one engineer from the eventual full text. Not a precise score.
- keep: true if it should advance to deep scoring. KEEP concrete methods/systems/architectures \
with a buildable core. DROP surveys, position/opinion papers, and purely theoretical work with \
no artifact to build.
- reasoning: one short sentence.

Return exactly one result per input paper, echoing its arxiv_id."""


def _format_papers(papers: Sequence[dict[str, Any]]) -> str:
    """Render the batch as a numbered list of id / title / abstract blocks."""
    blocks: list[str] = []
    for i, paper in enumerate(papers, start=1):
        arxiv_id = paper.get("arxiv_id", "unknown")
        title = paper.get("title", "Unknown title")
        abstract = (paper.get("abstract") or "").strip()
        blocks.append(f"{i}. arXiv:{arxiv_id}\nTitle: {title}\nAbstract: {abstract}")
    return "\n\n".join(blocks)


def get_triage_batch_prompt(papers: Sequence[dict[str, Any]]) -> tuple[str, str]:
    """Build the batched-triage prompt.

    Args:
        papers: batch of dicts, each with at least {arxiv_id, title, abstract}.

    Returns:
        (system_prompt, user_prompt).
    """
    user = (
        f"Triage the following {len(papers)} papers. Return one verdict per paper, in the "
        f"same order, each echoing its arxiv_id.\n\n"
        f"{_format_papers(papers)}"
    )
    return TRIAGE_SYSTEM_PROMPT, user
