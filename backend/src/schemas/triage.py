"""Schemas for Stage 1 cheap triage (the scoring pipeline's entry point).

Stage 1 crawls new arXiv submissions (title + abstract only, no PDF) and runs a single
coarse keep/drop classification over a batch of abstracts on the cheap default model.
Survivors are enqueued into Stage 2 deep scoring; the bulk (~70-80%) is dropped before any
full-text cost is incurred. See `docs/design/scoring-pipeline.md` -> "Stage 1 -- Cheap Triage".

This is deliberately lighter than the Stage 2 `DimensionScore` schema in
`schemas/scoring_state.py`: one verdict per paper, no evidence spans.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PaperClass = Literal["method", "survey", "benchmark", "theory", "position"]


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
