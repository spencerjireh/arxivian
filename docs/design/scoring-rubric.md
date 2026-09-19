# Scoring Rubric (v2)

The concrete scoring rubric behind `docs/design/scoring-pipeline.md`. That doc names the
dimensions and weights; this one pins what each dimension **asks** and how the answers
**combine**, so the scoring nodes have something to execute and the golden set has something
to be labeled against. The questions live in code at
`backend/src/services/scoring_service/questions.py` and the combine rules in
`backend/src/services/scoring_service/judgments.py`; keep this doc and those files in sync and
bump `RUBRIC_VERSION` (`backend/src/schemas/scoring_state.py`) when they change.

**`rubric_version = "v2"`** (2026-09-19). v1 rows in `paper_scores` stay readable but no
longer feed the digest. Judge instructions sharpened 2026-09-19 (SPE-295, no version bump:
levels and combine rules unchanged) -- see the notes under resource feasibility and data
availability.

v2 scores four dimensions with **zero GitHub dependency**. Code gap is deferred to v1.1.

## What changed from v1

v1 asked gpt-5-nano for a 0-100 number per judged dimension and used a keyword rule for the
data gate. v2 asks TypeSafe **Jev** (a System One model: typed judgments with calibrated
probabilities, no text generation) a set of atomic questions per dimension and combines the
answers in code. The stored truth is a **distribution over ordered levels plus the atomic
judgments**; the 0-100 number is derived from it. Nano remains only in Stage 1 triage.

## Storage shape

Each dimension persists a `DimensionScore` (in `paper_scores.dimensions` JSONB):

| Field | Meaning |
|---|---|
| `level` | argmax level (ties resolve to the lower, more conservative level) |
| `max_level` | levels run `0..max_level` |
| `expected` | probability-weighted mean level |
| `probabilities` | `P(level)` for every level |
| `confidence` | mass on the argmax |
| `judgments` | the atomic Jev answers (key, kind, answer, probabilities, confidence) |
| `evidence` | the spans sent as state, truncated |
| `reasoning` | code-generated summary of the judgments |

`derived_score()` maps the distribution to the **0-100 integer** used for ranking, the
digest gate filter, and band agreement. It is recomputable and is persisted only as a
denormalization (`paper_scores.*_score`). Per dimension:

| Dimension | `max_level` | derived score |
|---|---|---|
| method_clarity | 4 | `round(expected / 4 * 100)` |
| resource_feasibility | 4 | `round(expected / 4 * 100)` |
| data_availability | 1 | `100` if `level == 1` (PASS) else `0` |
| demand | 2 | `{0: 20, 1: 55, 2: 85}[level]` |

## Scale and bands

Hand labels and eval agreement use **coarse bands** over the derived score, because exact
numeric agreement across dozens of papers is neither reproducible nor meaningful:

| Band | Range | Meaning |
|---|---|---|
| `LOW` | 0-39 | weak / absent |
| `MED` | 40-69 | partial / mixed |
| `HIGH` | 70-100 | strong |

The eval buckets the derived score into these bands (`score_to_band` in
`schemas/scoring_state.py`) and checks agreement with the hand-labeled band. Data
availability is a gate, labeled `PASS` / `FAIL`.

## Dimensions

### 1. Method clarity -- 4 Jev Nouls, weight High

How reproducible the core contribution is from the paper alone, for an individual engineer.
Judges specification clarity only -- **not** novelty, correctness, or importance.

State: `abstract`, `method` (section, 12k-char cap), `experiments` (12k cap),
`pseudocode_spans` (retrieved chunks), `code_mentions`.

Four independent yes/no criteria, each a Noul returning P(yes):

| Key | Criterion |
|---|---|
| `algorithm_given` | an explicit algorithm, pseudocode, or equations sufficient to implement the core method |
| `architecture_specified` | the architecture is fully specified (layers and arrangement, dimensions, or a standard architecture plus stated modifications) |
| `hyperparameters_stated` | the hyperparameters for the main result are stated (a partial list with key values counts) |
| `training_procedure_described` | the training/fitting procedure and preprocessing are described in enough detail to run |

Combine: level = number of criteria satisfied; the distribution over 0..4 is the
**Poisson-binomial** of the four P(yes); `expected = sum(p)`. Band correspondence: LOW = 0-1
criteria, MED = 2, HIGH = 3-4 (via the derived score).

Evidence (`kind="pseudocode"`): the retrieved pseudocode / algorithm / hyperparameter spans.

### 2. Resource feasibility -- 1 Jev Score + 2 auxiliary Nouls, weight High

Whether an individual could realistically reproduce the core result on their own hardware or a
modest cloud budget. Intrinsic compute demand normalized to a solo-builder scale; the per-user
compute-profile match layers on **at read time**. **Higher level = more feasible / cheaper.**

State: `abstract`, `experiments`, `compute_spans` (retrieved chunks).

`compute_tier` Score, five concrete levels:

| Level | Situation |
|---|---|
| 0 | cluster scale: multi-node GPU/TPU clusters, TPU pods, thousands of GPU-hours |
| 1 | multi-GPU single node for days, or hundreds of GPU-hours |
| 2 | one A100/H100-class GPU for hours to a few days, or modest cloud spend |
| 3 | one 3090/4090-class consumer GPU, or a few cloud GPU-hours |
| 4 | laptop, CPU, or free-tier notebook GPU within hours |

Instruction notes (SPE-295): the tier is judged at the smallest scale that still demonstrates
the claim, so a cheap technique stays feasible even when the headline run used a cluster; but
when the trained model **is** the claim (a pretraining recipe, a foundation model, a
from-scratch generative model) the training cost counts, and fine-tuning released weights does
not reproduce it. Stated hardware is converted to single-A100 equivalents (~3 P100/V100
GPU-hours per A100-hour); inference-only methods against a hosted model API are level 3-4.

Auxiliary Nouls, recorded as judgments but **not combined** (a compute tier is a single
ordinal judgment; splitting it would break the relationship being judged):
`compute_stated` (the paper states its compute), `pretrained_weights_released`.

Combine: the dimension distribution is the Score's own distribution; `expected` is the
Score's expected level. Bands: LOW = 0-1, MED = 2, HIGH = 3-4.

Evidence (`kind="compute"`): retrieved GPU/TPU type and count, training time, parameter count.

### 3. Data availability -- 1 Jev Choice, disqualifying gate

State: `abstract`, `dataset_spans` (retrieved chunks).

`data_access` Choice over six options:

| Option | Gate side |
|---|---|
| public benchmark or standard dataset | PASS |
| released by the authors | PASS |
| synthetic or generated | PASS |
| not stated | PASS (recall-biased default, as in v1) |
| available on request or under license | FAIL |
| proprietary or private | FAIL |

The question asks for the data needed to **demonstrate the core claim**: a data-agnostic
method whose claim is demonstrable on a standard public dataset is "public benchmark" even
when the headline experiment used an internal corpus (word2vec, knowledge distillation);
"proprietary or private" is reserved for claims that cannot be demonstrated without data the
authors did not release (CLIP, PaLM, Whisper).

Combine: `P(PASS)` = summed mass of the PASS options; `level = 1` when `P(PASS) >= 0.5`.
The gate decides on the argmax, so the digest filter `data_availability_score == 100` is
exact. A paper no one else can get the data for is not individually implementable,
regardless of the other scores.

Evidence (`kind="dataset"`): retrieved dataset mentions.

### 4. Demand -- Semantic Scholar API (no Jev), weight Medium

Citation velocity (citations per month since publication) bucketed into a band. **This
dimension is not scored from paper text.** Represented as a one-hot level
(`LOW = 0`, `MED = 1`, `HIGH = 2`, confidence 1.0) so the stored shape is uniform.

Provisional band mapping (to be recalibrated against the real S2 velocity distribution):

| Band | Rough citations/month |
|---|---|
| `HIGH` | high-velocity, widely-cited |
| `MED` | steady but modest |
| `LOW` | little uptake |

Evidence (`kind="citation"`): citation count + velocity from the S2 lookup. A soft-failed
lookup (no key, 429) persists NULL; the composite excludes it and renormalizes the remaining
weights (SPE-284), so a failed lookup does not read as low demand.

## Product attributes (not ranking signals)

Asked on the method-clarity request (same state) and stored in `paper_scores.attributes`:

| Key | Kind | Meaning |
|---|---|---|
| `code_released` | Noul | the authors state they release the code; `code_mentions` (repo URLs + code-availability sentences from the raw text) is the state |
| `task_type` | Choice | closed set: language modeling, machine translation, text classification or understanding, question answering, image classification, object detection or segmentation, image or video generation, reinforcement learning or control, speech, other |
| `model_family` | Choice | closed set: transformer, convolutional network, recurrent network, diffusion model, graph neural network, classical machine learning, other |

`code_released` is judged from the paper's own statements. It is **not** the v1.1 code-gap
signal (a GitHub search for third-party implementations) and must not be surfaced as
"no existing code".

## Composite and the `implementable` label

**Composite weights are a proposed default, not final** -- the exact formula is a tuning
decision (`scoring-pipeline.md` Open Question 3). Proposed starting point, over the derived
scores:

```
composite = gate * (0.35 * method_clarity + 0.35 * resource_feasibility + 0.30 * demand)
where gate = 0 if data_availability == FAIL else 1
```

NULL sub-scores (a soft-failed lookup) are excluded and the remaining weights renormalize to
1 (`compute_composite` in `schemas/digest.py`); all-NULL is 0.

The golden set's binary **`implementable`** flag is the label the agreement gate measures
against. Rule:

```
implementable = (data_availability == PASS)
                and (method_clarity   >= MED)
                and (resource_feasibility >= MED)
```

A paper can be novel and highly cited yet **not** implementable (proprietary data, or
cluster-scale compute) -- that is exactly the judgment the feed exists to make, and the
failure mode the eval guards against (a cluster-scale paper mislabeled "single-GPU feasible").

## Calibration

Jev's `confidence` per dimension is the mass on the argmax level. The eval prints the mean
of the per-paper minimum confidence for papers whose `implementable` prediction agrees vs
disagrees with the label (`test_calibration_report`). The product should use a low
per-dimension confidence as a "low confidence" marker on the card rather than hiding it.

## Open items

- Numeric composite weights (above) are provisional; tune against the golden set.
- Demand normalization thresholds need real Semantic Scholar velocity data.
- Option sets for `task_type` and `model_family` are first guesses; revise after inspecting
  real outputs (the spike showed BERT fits no task option).
- **Band-boundary sensitivity.** Scores near a cutoff flip bands, so exact-band agreement
  will always carry some noise. The robust primary gate is the `implementable` binary above,
  which is insensitive to a single adjacent-band shift (MED and HIGH both satisfy `>= MED`).
  The eval reports adjacent-band tolerance alongside exact agreement.
