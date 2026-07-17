# Scoring Rubric (v1)

The concrete scoring rubric behind `docs/design/scoring-pipeline.md`. That doc names the
dimensions and weights; this one pins the **anchors** -- what a score actually means per
dimension -- so the LLM nodes have something to execute and the golden set has something to
be labeled against. The band anchors here are mirrored in code at
`backend/src/services/scoring_service/prompts.py`; keep the two in sync and bump
`RUBRIC_VERSION` (`backend/src/schemas/scoring_state.py`) when they change.

**`rubric_version = "v1"`**

v1 scores four dimensions with **zero GitHub dependency**. Code gap is deferred to v1.1.

## Scale and bands

Every dimension stores a **0-100 integer** sub-score (globally, per paper -- the user-weighted
composite is computed at read time). Hand labels and eval agreement use **coarse bands**,
because exact numeric agreement across dozens of papers is neither reproducible nor meaningful:

| Band | Range | Meaning |
|---|---|---|
| `LOW` | 0-39 | weak / absent |
| `MED` | 40-69 | partial / mixed |
| `HIGH` | 70-100 | strong |

The eval buckets the model's 0-100 output into these bands (`score_to_band` in
`schemas/scoring_state.py`) and checks agreement with the hand-labeled band. Data
availability is a gate, labeled `PASS` / `FAIL`.

## Dimensions

### 1. Method clarity -- LLM (stronger model), weight High

How reproducible the core contribution is from the paper alone, for an individual engineer.
Judges specification clarity only -- **not** novelty, correctness, or importance.

- **HIGH** -- explicit pseudocode or a numbered algorithm, stated hyperparameters, fully
  specified architecture. Reimplementable from the paper.
- **MED** -- prose method with partial detail; some hyperparameters/architecture stated but
  gaps that would require guessing.
- **LOW** -- vague / hand-wavy; the mechanism is asserted, not specified.

Evidence (`kind="pseudocode"`): quoted pseudocode / algorithm / hyperparameter / architecture
spans.

### 2. Resource feasibility -- LLM (stronger model), weight High

Whether an individual could realistically reproduce the core result on their own hardware or a
modest cloud budget. This is the paper's **intrinsic** compute demand normalized to a
solo-builder scale; the per-user compute-profile match (laptop / single GPU / cloud) layers on
**at read time** and is not baked into this sub-score. **Higher score = more feasible / cheaper.**

- **HIGH** -- laptop, single consumer GPU (one 3090/4090), or CPU-scale.
- **MED** -- one high-end/datacenter GPU (e.g. an A100), or modest affordable cloud hours.
- **LOW** -- multi-node clusters, hundreds/thousands of GPU-hours, TPU pods.

Evidence (`kind="compute"`): quoted GPU/TPU type and count, training time, parameter count.

### 3. Data availability -- deterministic gate (extraction), disqualifying

Not an LLM judgment. Extraction pulls dataset mentions; a rule decides the gate.

- **PASS** -- public/standard/synthetic datasets (ImageNet, C4, Wikipedia, generated data, ...).
- **FAIL** -- proprietary / clinical / private / internal / licensed-inaccessible data. A paper
  no one else can get the data for is not individually implementable, regardless of the other
  scores.

Evidence (`kind="dataset"`): quoted dataset mentions. In `DimensionScore` the gate is carried
as `score in {0, 100}` (100 = PASS, 0 = FAIL).

### 4. Demand -- Semantic Scholar API (no LLM), weight Medium

Citation velocity (citations per month since publication) bucketed into a band. **This
dimension is not scored from paper text.** The Semantic Scholar client lands in **Phase 1**;
until then, golden-set demand labels are **provisional** (coarse, from general knowledge) and
should not be trusted for agreement measurement.

Provisional band mapping (to be recalibrated in Phase 1 against the real S2 velocity
distribution -- an open item):

| Band | Rough citations/month |
|---|---|
| `HIGH` | high-velocity, widely-cited |
| `MED` | steady but modest |
| `LOW` | little uptake |

Evidence (`kind="citation"`): citation count + velocity from the S2 lookup.

## Composite and the `implementable` label

**Composite weights are a proposed default, not final** -- `proposal.md` §5.1 gives only
ordinal weights, and the exact formula is a Phase-1 tuning decision (`scoring-pipeline.md`
Open Question 3). Proposed starting point:

```
composite = gate * (0.35 * method_clarity + 0.35 * resource_feasibility + 0.30 * demand)
where gate = 0 if data_availability == FAIL else 1
```

The golden set's binary **`implementable`** flag is the label the >=85% feasibility-agreement
target measures against. Rule:

```
implementable = (data_availability == PASS)
                and (method_clarity   >= MED)
                and (resource_feasibility >= MED)
```

A paper can be novel and highly cited yet **not** implementable (proprietary data, or
cluster-scale compute) -- that is exactly the judgment the feed exists to make, and the
failure mode the eval guards against (a cluster-scale paper mislabeled "single-GPU feasible").

## Open items

- Numeric composite weights (above) are provisional; tune against the golden set in Phase 1.
- Demand normalization thresholds need real Semantic Scholar velocity data (Phase 1).
- No `scoring_strong_model` config setting exists yet; the two LLM dimensions target
  `openai/gpt-4o-mini` from `allowed_llm_models`. The setting is added in Phase 1.
- **Band-boundary sensitivity (finding from the Phase 0 smoke run).** Scores near a cutoff
  (e.g. 60 vs 70) flip bands, so exact-band agreement will always carry some noise. The
  robust primary gate is the `implementable` binary above, which is insensitive to a single
  adjacent-band shift (MED and HIGH both satisfy `>= MED`). When the Phase 1 eval measures
  per-dimension agreement, allow adjacent-band tolerance (or weight the `implementable`
  agreement) rather than demanding exact band matches.
