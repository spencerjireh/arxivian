"""Scoring pipeline state and structured-output models (Stage 2 deep scoring).

Backbone of the feed pivot's scoring graph. Mirrors the conventions in
`schemas/langgraph_state.py`: flat Pydantic models with `extra="forbid"`, integer
sub-scores with explicit bounds, and field descriptions that double as instructions for
the prompt-injected-JSON path (the cheap default provider is not in
`NATIVE_STRUCTURED_OUTPUT_PROVIDERS`, so keep these schemas modest).

v1 scores four dimensions -- method clarity, resource feasibility, data availability,
demand. Only method clarity and resource feasibility are LLM-judged; the schema is shared
across all four. Code gap is deferred to v1.1 (see `docs/design/scoring-pipeline.md`).
"""

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

# Rubric revision these schemas encode. Bump when anchors/weights change so stored
# `paper_scores` rows remain interpretable. See `docs/design/scoring-rubric.md`.
RUBRIC_VERSION = "v1"

# Band boundaries used to bucket a 0-100 score into a coarse label for eval agreement.
# LOW [0,40) - MED [40,70) - HIGH [70,100].
Band = Literal["LOW", "MED", "HIGH"]

EvidenceKind = Literal["pseudocode", "compute", "dataset", "citation"]


def score_to_band(score: int) -> Band:
    """Bucket a 0-100 sub-score into its coarse band (matches the golden-set labels)."""
    if score < 40:
        return "LOW"
    if score < 70:
        return "MED"
    return "HIGH"


class EvidenceSpan(BaseModel):
    """A single quoted span (or external hit) that supports a sub-score.

    Store-evidence-not-numbers: every sub-score must point back to one of these so the
    UI breakdown is auditable and the rubric stays tunable.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="The exact quoted span from the paper (or an external result)")
    kind: EvidenceKind = Field(..., description="What this span evidences: pseudocode, compute, dataset, or citation")
    source: str = Field(
        default="",
        description="Where the span came from, e.g. a section name, 'abstract', or an external URL",
    )


class DimensionScore(BaseModel):
    """One rubric dimension's global sub-score plus its supporting evidence.

    `score` is 0-100. For the data-availability gate, score is used as a flag: 100 = the
    gate passes (accessible data), 0 = it fails (proprietary/inaccessible, disqualifying).
    """

    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(..., description="Dimension name, e.g. 'method_clarity'")
    score: int = Field(..., ge=0, le=100, description="Sub-score 0-100 (0 or 100 for the data-availability gate)")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Quoted spans that justify the score; empty only when genuinely no signal exists",
    )
    reasoning: str = Field(..., description="Brief explanation of the score, referencing the evidence")


class PaperScoreState(TypedDict):
    """State passed between scoring-graph nodes (mirrors `AgentState`).

    Each parallel dimension writes a DISTINCT key so the last-write-wins merge never
    collides (house style -- no reducers outside `messages`).
    """

    paper_id: str
    arxiv_id: str

    # Candidate evidence extracted up front by fetch_and_extract: pseudocode / compute /
    # dataset spans, keyed by kind.
    extracted_spans: dict

    # One result per v1 dimension.
    method_clarity_result: DimensionScore
    resource_feasibility_result: DimensionScore
    data_availability_result: DimensionScore
    demand_result: DimensionScore
    # code_gap_result: DimensionScore   # v1.1 -- added with the github_search node

    rubric_version: str
