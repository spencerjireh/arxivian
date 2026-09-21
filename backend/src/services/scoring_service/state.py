"""Scoring pipeline state and stored-score models (Stage 2 deep scoring, rubric v2).

Backbone of the feed pivot's scoring graph. Mirrors the conventions in
`services/agent_service/state.py`: flat Pydantic models with `extra="forbid"` and field
descriptions that double as documentation for the JSONB payloads.

v2 stores judgments natively: every dimension is a distribution over ordered levels
(from TypeSafe Jev) plus the atomic judgments that produced it. The 0-100 integer used
for ranking is *derived* (`DimensionScore.derived_score`) and recomputable; it is
persisted only as a denormalization for the digest query. Demand is still a Semantic
Scholar lookup, represented as a one-hot level. See `docs/design/scoring-rubric.md`.
"""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

# Rubric revision these schemas encode. Bump when anchors/levels/combine rules change so
# stored `paper_scores` rows remain interpretable. See `docs/design/scoring-rubric.md`.
RUBRIC_VERSION = "v2"

# Band boundaries used to bucket a derived 0-100 score into a coarse label for eval
# agreement. LOW [0,40) - MED [40,70) - HIGH [70,100].
Band = Literal["LOW", "MED", "HIGH"]

EvidenceKind = Literal["pseudocode", "compute", "dataset", "citation", "code"]

JudgmentKind = Literal["noul", "choice", "score"]

# Demand: Semantic Scholar velocity band -> level, and level -> derived 0-100 value.
DEMAND_LEVELS: dict[str, int] = {"LOW": 0, "MED": 1, "HIGH": 2}
DEMAND_LEVEL_TO_SCORE: dict[int, int] = {0: 20, 1: 55, 2: 85}
DEMAND_BAND_TO_SCORE: dict[str, int] = {
    band: DEMAND_LEVEL_TO_SCORE[lvl] for band, lvl in DEMAND_LEVELS.items()
}

# Max level per dimension (levels are 0..max_level inclusive).
DIMENSION_MAX_LEVEL: dict[str, int] = {
    "method_clarity": 4,  # 0..4 clarity criteria satisfied
    "resource_feasibility": 4,  # compute tier 0 (cluster) .. 4 (laptop)
    "data_availability": 1,  # 0 FAIL, 1 PASS
    "demand": 2,  # LOW / MED / HIGH
}


def score_to_band(score: int) -> Band:
    """Bucket a derived 0-100 sub-score into its coarse band (matches the golden-set labels)."""
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

    text: str = Field(
        ..., description="The exact quoted span from the paper (or an external result)"
    )
    kind: EvidenceKind = Field(
        ..., description="What this span evidences: pseudocode, compute, dataset, citation, or code"
    )
    source: str = Field(
        default="",
        description="Where the span came from, e.g. a section name, 'abstract', or an external URL",
    )


class Judgment(BaseModel):
    """One atomic Jev answer (a Noul, Choice, or Score) as asked by a dimension node.

    `probabilities` keys are strings so the payload round-trips through JSONB unchanged
    (Noul: "yes"/"no"; Choice: option labels; Score: level numbers as strings).
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Question key, e.g. 'algorithm_given'")
    kind: JudgmentKind
    answer: str | int | bool = Field(
        ..., description="Argmax answer (bool for Nouls, label for Choices, level for Scores)"
    )
    probabilities: dict[str, float]
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Concentration of the distribution (max probability)"
    )
    legend: list[str] | None = Field(
        default=None, description="Score level descriptions, in level order"
    )


class DimensionScore(BaseModel):
    """One rubric dimension: a distribution over ordered levels plus its provenance.

    `level` is the argmax, `expected` the probability-weighted mean level, `confidence`
    the mass on the argmax. `judgments` are the atomic answers combined into this
    distribution (see `scoring_service/judgments.py`).
    """

    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(..., description="Dimension name, e.g. 'method_clarity'")
    level: int = Field(..., ge=0)
    max_level: int = Field(..., ge=1)
    expected: float = Field(..., ge=0.0)
    probabilities: dict[int, float] = Field(
        ..., description="P(level) for every level 0..max_level"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    judgments: list[Judgment] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Quoted spans that were sent as state and justify the score",
    )
    reasoning: str = Field(..., description="Code-generated summary of the judgments")

    def derived_score(self) -> int:
        """The 0-100 integer used for ranking and bands. Recomputable from the distribution.

        Per dimension: method_clarity / resource_feasibility normalize the expected level;
        data_availability is binary on the argmax (so the digest gate filter `== 100`
        stays exact); demand maps its level to the fixed band values.
        """
        if self.dimension == "data_availability":
            return 100 if self.level == 1 else 0
        if self.dimension == "demand":
            return DEMAND_LEVEL_TO_SCORE[self.level]
        return round(self.expected / self.max_level * 100)

    def band(self) -> Band:
        return score_to_band(self.derived_score())

    @classmethod
    def from_jsonb(cls, data: dict[str, Any]) -> "DimensionScore":
        """Rebuild from a `paper_scores.dimensions[<dim>]` payload.

        JSONB stores the `probabilities` keys as strings; pydantic's lax mode coerces
        them back to int here. This is the one read-side coercion point.
        """
        return cls.model_validate(data)


class PaperAttributes(BaseModel):
    """Non-ranking product attributes judged alongside method clarity."""

    model_config = ConfigDict(extra="forbid")

    code_released: Judgment
    task_type: Judgment
    model_family: Judgment


class PaperScoreState(TypedDict):
    """State passed between scoring-graph nodes (mirrors `AgentState`).

    Each parallel dimension writes DISTINCT keys so the last-write-wins merge never
    collides (house style -- no reducers outside `messages`).
    """

    paper_id: str
    arxiv_id: str

    # Paper identity: at least {title, arxiv_id, abstract}. Populated by fetch_and_extract
    # from the ingested paper row.
    paper_meta: dict

    # Candidate evidence extracted up front by fetch_and_extract: pseudocode / compute /
    # dataset probe chunks and code_mentions, keyed by kind (each a list of spans).
    extracted_spans: dict

    # Section payloads from `utils.section_splitter.extract_sections`: abstract, method,
    # experiments, appendix_headings (strings, capped).
    sections: dict

    # One result per dimension. `None` marks a dimension that soft-failed (its column
    # persists NULL) -- the columns are nullable by design, so a paper can be partially
    # scored rather than lost.
    method_clarity_result: DimensionScore | None
    resource_feasibility_result: DimensionScore | None
    data_availability_result: DimensionScore | None
    demand_result: DimensionScore | None
    # v1.1 adds code_gap_result here together with the github_search node.

    # Product attributes ride on the method_clarity request (same state).
    attributes_result: PaperAttributes | None

    # Per-request usage, one key per Jev-backed node: {"model": str, "input_tokens": int|None}.
    method_clarity_usage: dict | None
    resource_feasibility_usage: dict | None
    data_availability_usage: dict | None

    rubric_version: str
