"""Stage 1 cheap triage: result schemas and the batched abstract-classification prompt.

Stage 1 crawls new arXiv submissions (title + abstract only, no PDF) and runs a single
coarse keep/drop classification over a batch of abstracts on the cheap default model.
Survivors are enqueued into Stage 2 deep scoring; the bulk (~70-80%) is dropped before any
full-text cost is incurred. See `ARX-55` -> "Stage 1 -- Cheap Triage".

The schema is deliberately lighter than the Stage 2 `DimensionScore` in `state.py`: one
verdict per paper, no evidence spans. The prompt is NOT one of the Stage 2 rubric
dimensions; it is recall-biased elimination of the obvious non-candidates (surveys,
position papers, non-implementable theory). Output is validated against
`TriageBatchResult` by `generate_structured`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PaperClass = Literal["method", "survey", "benchmark", "theory", "position"]

_ARXIV_ID_PREFIX_RE = re.compile(
    r"^(?:https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/|arxiv:)", re.IGNORECASE
)
_ARXIV_ID_SUFFIX_RE = re.compile(r"(?:v\d+)?(?:\.pdf)?$", re.IGNORECASE)


def normalize_arxiv_id(raw: str) -> str:
    """Reduce an arXiv id as an LLM or a user may write it to the bare form the crawl uses.

    Strips whitespace, an `arXiv:` prefix or an arxiv.org abs/pdf URL, a `vN` version and
    a `.pdf` suffix: `arXiv:2609.22064v2` -> `2609.22064`. The crawl stores ids bare and
    unversioned (`clients/arxiv_client.py`), and the LLM echo must match them exactly.
    """
    value = raw.strip()
    value = _ARXIV_ID_PREFIX_RE.sub("", value)
    return _ARXIV_ID_SUFFIX_RE.sub("", value)


class TriageResult(BaseModel):
    """One coarse keep/drop verdict for a single crawled abstract."""

    model_config = ConfigDict(extra="forbid")

    arxiv_id: str
    paper_class: PaperClass
    rough_implementability: int = Field(..., ge=0, le=100)
    keep: bool  # survives to Stage 2
    reasoning: str


class TriageBatchResult(BaseModel):
    """Wrapper so a single `generate_structured` call classifies a whole batch.

    `generate_structured` returns one object, so batching N abstracts into one LLM call
    requires the response schema to hold a list.
    """

    model_config = ConfigDict(extra="forbid")

    results: list[TriageResult]


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
    """Render the batch as a numbered list of id / title / abstract blocks.

    The id is rendered bare (no `arXiv:` prefix) so the echoed `arxiv_id` matches the
    crawled id; `normalize_arxiv_id` on the consumer side covers a decorated echo anyway.
    """
    blocks: list[str] = []
    for i, paper in enumerate(papers, start=1):
        arxiv_id = paper.get("arxiv_id", "unknown")
        title = paper.get("title", "Unknown title")
        abstract = (paper.get("abstract") or "").strip()
        blocks.append(f"{i}. arxiv_id: {arxiv_id}\nTitle: {title}\nAbstract: {abstract}")
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
