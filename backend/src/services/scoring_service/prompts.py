"""Prompt templates for the scoring graph's LLM-judged dimensions.

Only two of the four v1 dimensions are genuine LLM judgments -- method clarity and
resource feasibility -- and both run on the stronger model. Data availability is a
deterministic gate over extracted dataset mentions and demand is a Semantic Scholar
lookup, so neither has a prompt here.

Mirrors `agent_service/prompts.py`: system-prompt constants that embed the rubric band
anchors, plus builder functions that return a `(system_prompt, user_prompt)` tuple. The
band anchors are the code-side copy of `docs/design/scoring-rubric.md` -- keep them in
sync, and bump `RUBRIC_VERSION` in `schemas/scoring_state.py` when they change.

Output is validated against `DimensionScore` by `generate_structured`; the JSON schema is
appended automatically on the prompt-injected path, so these prompts describe *how to
score*, not the output shape.
"""

from __future__ import annotations

# --- Band scale shared by both dimensions ------------------------------------------------
# The pipeline stores a 0-100 sub-score; the golden set labels coarse bands. Anchor the
# numeric score to these ranges so bucketing (LOW [0,40) / MED [40,70) / HIGH [70,100])
# agrees with the hand labels.
_SCORE_SCALE = """SCORE SCALE (0-100, must line up with the coarse bands):
- 70-100 (HIGH): strong on this dimension
- 40-69  (MED):  partial / mixed
- 0-39   (LOW):  weak / absent
Pick a number inside the band your judgment lands in; do not hug the boundaries."""


SCORE_METHOD_CLARITY_SYSTEM_PROMPT = f"""You score how clearly a paper specifies its method -- i.e. how reproducible the core \
contribution is from the paper alone, for an individual engineer.

ANCHORS:
- HIGH (70-100): explicit pseudocode or a numbered algorithm, stated hyperparameters, and a \
fully specified architecture. A competent engineer could reimplement it from the paper.
- MED (40-69): the method is described in prose with partial detail -- some hyperparameters \
or architectural choices are stated, but there are gaps that would require guessing.
- LOW (0-39): vague or hand-wavy. The core mechanism is asserted but not specified; no \
reproducible detail.

{_SCORE_SCALE}

RULES:
- Judge ONLY specification clarity, not novelty, correctness, or importance.
- Ground the score in the provided candidate spans. Quote the exact pseudocode / \
hyperparameter / architecture text you relied on as evidence (kind="pseudocode").
- If the candidate spans are empty or unhelpful, say so and score LOW -- do not invent detail.
- Set dimension="method_clarity"."""


SCORE_RESOURCE_FEASIBILITY_SYSTEM_PROMPT = f"""You score whether an individual builder could realistically reproduce a paper's core \
result on their own hardware or a modest cloud budget. This is the paper's INTRINSIC \
compute demand -- do not assume a specific user's machine (per-user compute matching happens \
later). A HIGHER score means MORE feasible / CHEAPER.

ANCHORS:
- HIGH (70-100): laptop, single consumer GPU (e.g. one 3090/4090), or CPU-scale. Minutes to \
a few hours on one device.
- MED (40-69): a single high-end/datacenter GPU (e.g. one A100), or modest affordable cloud \
hours. A determined individual could still manage it.
- LOW (0-39): multi-node clusters, hundreds/thousands of GPU-hours, TPU pods, or training \
runs that cost more than a hobbyist would spend. Reproducing the full result is out of reach \
for an individual.

{_SCORE_SCALE}

RULES:
- Base the score on stated compute: GPU/TPU type and count, training time, parameter count, \
dataset scale. Quote the exact compute text as evidence (kind="compute").
- Score the cost to REPRODUCE THE CORE RESULT. If a smaller-scale variant is clearly \
described and cheap, judge that; otherwise judge the headline run.
- If no compute details are stated, reason from model/data scale and note the uncertainty; \
do not default to HIGH just because compute is unmentioned.
- Set dimension="resource_feasibility"."""


def _format_spans(extracted_spans: dict, keys: list[str]) -> str:
    """Render candidate evidence spans for the given keys into a compact prompt block."""
    parts: list[str] = []
    for key in keys:
        spans = extracted_spans.get(key) or []
        if not spans:
            continue
        joined = "\n".join(f"  - {str(s)[:600]}" for s in spans)
        parts.append(f"{key}:\n{joined}")
    return "\n\n".join(parts) if parts else "(no candidate spans extracted)"


def _paper_header(paper_meta: dict) -> str:
    """One-line paper identity for the user prompt."""
    title = paper_meta.get("title", "Unknown title")
    arxiv_id = paper_meta.get("arxiv_id", "unknown")
    return f"Paper: {title} (arXiv:{arxiv_id})"


def get_method_clarity_prompt(extracted_spans: dict, paper_meta: dict) -> tuple[str, str]:
    """Build the method-clarity scoring prompt.

    Args:
        extracted_spans: fetch_and_extract output; uses the "pseudocode" key (algorithm
            blocks, stated hyperparameters, architecture spans).
        paper_meta: at least {title, arxiv_id, abstract}.

    Returns:
        (system_prompt, user_prompt).
    """
    abstract = paper_meta.get("abstract", "")
    spans = _format_spans(extracted_spans, ["pseudocode"])
    user = (
        f"{_paper_header(paper_meta)}\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Candidate method/specification spans extracted from the full text:\n{spans}\n\n"
        "Score method clarity per the anchors. Quote the spans you used as evidence."
    )
    return SCORE_METHOD_CLARITY_SYSTEM_PROMPT, user


def get_resource_feasibility_prompt(extracted_spans: dict, paper_meta: dict) -> tuple[str, str]:
    """Build the resource-feasibility scoring prompt.

    Args:
        extracted_spans: fetch_and_extract output; uses the "compute" key (GPU/TPU
            mentions, training time, parameter counts).
        paper_meta: at least {title, arxiv_id, abstract}.

    Returns:
        (system_prompt, user_prompt).
    """
    abstract = paper_meta.get("abstract", "")
    spans = _format_spans(extracted_spans, ["compute"])
    user = (
        f"{_paper_header(paper_meta)}\n\n"
        f"Abstract:\n{abstract}\n\n"
        f"Candidate compute/resource spans extracted from the full text:\n{spans}\n\n"
        "Score resource feasibility per the anchors (higher = cheaper to reproduce). "
        "Quote the compute spans you used as evidence."
    )
    return SCORE_RESOURCE_FEASIBILITY_SYSTEM_PROMPT, user
