"""Jev question definitions for the Stage 2 scoring graph (rubric v2).

Each question is one narrow judgment over named fields of the request state. Level and
option descriptions are concrete situations, not abstract degrees, per TypeSafe's Score /
Choice guidance; every Choice has an explicit no-match option. The dimension nodes send
these over the state built by `fetch_and_extract`; `judgments.py` combines the answers.

State field names referenced in backticks below must match the payloads built in
`nodes/dimensions.py`.
"""

from __future__ import annotations

from typesafe_sdk import Choice, Noul, Score

# --- Method clarity: four independent clarity criteria (Nouls) --------------------------
# Level = number satisfied. Each asks about the paper's *own* core method, judged from
# `method`, `experiments`, `pseudocode_spans` (retrieved candidate spans), and `abstract`.

METHOD_CLARITY_CRITERIA: tuple[str, ...] = (
    "algorithm_given",
    "architecture_specified",
    "hyperparameters_stated",
    "training_procedure_described",
)

METHOD_CLARITY_QUESTIONS: dict[str, Noul] = {
    "algorithm_given": Noul(
        instructions=(
            "Does the paper give an explicit algorithm, pseudocode, or equations that are "
            "sufficient to implement the core method described in `abstract`? Judge from "
            "`method`, `pseudocode_spans`, and `experiments`. A method described only in "
            "prose, with the mechanism asserted rather than specified, does not count."
        )
    ),
    "architecture_specified": Noul(
        instructions=(
            "Are the components of the proposed method fully specified in `method` or "
            "`experiments`, so that an engineer could build it without guessing? For a new "
            "model this means the layer types, their arrangement, and dimensions; for a "
            "technique applied to an existing model (a new layer, an adapter, a training "
            "trick, an objective) it means the exact modification plus a named base "
            "architecture. Judge the method itself, not whether every baseline is described."
        )
    ),
    "hyperparameters_stated": Noul(
        instructions=(
            "Are the hyperparameters needed to reproduce the main result stated in "
            "`experiments` or `method` (for example learning rate, batch size, optimizer, "
            "number of steps or epochs, model size)? A partial list with the key values "
            "counts; a statement that details are 'in the appendix' with none given does not."
        )
    ),
    "training_procedure_described": Noul(
        instructions=(
            "Is the procedure for training or applying the proposed method described in "
            "`method` or `experiments` in enough detail to run it: the objective or update "
            "rule, the optimizer or schedule, and any data preprocessing the method needs? "
            "A method that needs no training counts as yes if its inference procedure is "
            "described. Judge the method itself, not whether every baseline is described."
        )
    ),
}

# --- Resource feasibility: one ordinal compute tier (Score) + auxiliary Nouls ---------
# Higher level = more feasible for an individual. Levels describe concrete situations.

COMPUTE_TIER_LEVELS: list[str] = [
    "Cluster scale: the method only makes sense at a scale that needs multi-node GPU or "
    "TPU clusters, TPU pods, or thousands of GPU-hours (for example pretraining a "
    "billion-parameter model from scratch is the contribution itself).",
    "Multi-GPU node: a faithful reproduction of the core claim needs a single machine "
    "with several datacenter GPUs running for days, or hundreds of GPU-hours.",
    "Single datacenter GPU: a faithful reproduction of the core claim fits on one A100- "
    "or H100-class GPU for hours to a few days, or the equivalent modest cloud spend.",
    "Single consumer GPU: the core claim can be demonstrated on one 3090- or 4090-class "
    "GPU, or with a few cloud GPU-hours, for example by training a small or medium model "
    "or fine-tuning a released checkpoint.",
    "Laptop or CPU scale: the core claim can be demonstrated on a laptop, a CPU, or a "
    "free-tier notebook GPU within hours.",
]

COMPUTE_TIER = Score(
    instructions=(
        "What compute does an individual need to reproduce the paper's core claim with the "
        "described method, judged from `abstract`, `experiments`, and `compute_spans`? Judge "
        "the method's intrinsic cost at the smallest scale that still demonstrates the "
        "claim: a technique that is cheap to apply (a new layer, a fine-tuning method, a "
        "training trick, a small model) is feasible even when the authors' headline "
        "experiment used a large cluster. Only when large scale is the contribution itself "
        "does the headline cost apply. If the paper's core claim is the trained model itself "
        "(a pretraining recipe, a foundation model, or a from-scratch generative model whose "
        "output quality is the result), judge the cost to train that model; fine-tuning or "
        "running released weights does not reproduce the claim. Convert stated hardware to "
        "single-A100 equivalents: roughly 3 P100 or V100 GPU-hours per A100-hour; a few days "
        "on one A100 is level 2, several hundred A100-hours is level 1. Methods that only run "
        "inference against a hosted model API, with no training, are level 3 or 4. The "
        "hardware, training time, and model sizes the paper states are an upper bound. When "
        "compute is not stated, infer it from the model size and dataset; do not assume "
        "cluster scale."
    ),
    criteria=COMPUTE_TIER_LEVELS,
)

FEASIBILITY_AUX_QUESTIONS: dict[str, Noul] = {
    "compute_stated": Noul(
        instructions=(
            "Does the paper state the compute used for its main result in `experiments` or "
            "`compute_spans` (GPU or TPU type and count, training time, or total GPU-hours)?"
        )
    ),
    "pretrained_weights_released": Noul(
        instructions=(
            "Do the authors state in `abstract`, `experiments`, or `compute_spans` that they "
            "release trained model weights or checkpoints for the method?"
        )
    ),
}

# --- Data availability: one Choice regrouped into the PASS/FAIL gate ------------------

DATA_ACCESS = Choice(
    instructions=(
        "How can someone other than the authors obtain the data needed to demonstrate the "
        "paper's core claim, according to `abstract` and `dataset_spans`? Judge the primary "
        "training or evaluation data, not auxiliary baselines. If the method is "
        "data-agnostic and the paper also evaluates on, or the claim is demonstrable with, a "
        "standard public dataset, choose 'public benchmark or standard dataset' even when "
        "the headline experiment used an internal corpus. Choose 'proprietary or private' "
        "only when the claim cannot be demonstrated without data the authors did not release."
    ),
    criteria={
        "public benchmark or standard dataset": (
            "The data is a named public benchmark or standard dataset anyone can download, "
            "such as ImageNet, GLUE, C4, Wikipedia, or COCO."
        ),
        "released by the authors": (
            "The authors state that they release the dataset they built, with a download "
            "location or a statement that it is public."
        ),
        "synthetic or generated": (
            "The data is generated by a described procedure or simulator that a reader can re-run."
        ),
        "available on request or under license": (
            "The data is obtainable only by request, data use agreement, or a paid or "
            "restricted license."
        ),
        "proprietary or private": (
            "The data is proprietary, internal, clinical, patient, or otherwise private and "
            "not obtainable by the public."
        ),
        "not stated": "The text does not say where the data comes from or how to get it.",
    },
)

# Options whose mass counts toward PASS. "not stated" keeps the v1 default-PASS
# (recall-biased) behavior: the gate fails only on an explicit inaccessible signal.
GATE_PASS_OPTIONS: frozenset[str] = frozenset(
    {
        "public benchmark or standard dataset",
        "released by the authors",
        "synthetic or generated",
        "not stated",
    }
)

# --- Product attributes (ride on the method-clarity request) --------------------------

CODE_RELEASED = Noul(
    instructions=(
        "Do the authors state that they release or publish the source code for the method "
        "described in `abstract`? `code_mentions` lists repository URLs and code-related "
        "sentences found anywhere in the paper; a URL that belongs to someone else's prior "
        "work does not count."
    )
)

TASK_TYPE = Choice(
    instructions=(
        "Which task does the paper's proposed method primarily target, according to "
        "`abstract` and `method`?"
    ),
    criteria={
        "language modeling": "Predicting or generating text; includes large language model pretraining.",
        "machine translation": "Translating text between languages.",
        "text classification or understanding": (
            "Sentence or document classification, natural language inference, sentiment, "
            "GLUE-style benchmarks."
        ),
        "question answering": (
            "Answering questions from context or knowledge, including reading comprehension."
        ),
        "image classification": "Assigning labels to images.",
        "object detection or segmentation": "Localizing objects or pixels in images.",
        "image or video generation": "Synthesizing images or video.",
        "reinforcement learning or control": "Learning policies from rewards.",
        "speech": "Speech recognition, synthesis, or audio.",
        "other": "A task not listed above, or a method paper with no single target task.",
    },
)

MODEL_FAMILY = Choice(
    instructions=(
        "Which model family is the paper's proposed or studied model, according to "
        "`abstract` and `method`?"
    ),
    criteria={
        "transformer": "Self-attention based encoder, decoder, or encoder-decoder.",
        "convolutional network": "CNN-based architecture.",
        "recurrent network": "RNN, LSTM, or GRU based architecture.",
        "diffusion model": "Denoising diffusion or score-based generative model.",
        "graph neural network": "Message passing over graph structure.",
        "classical machine learning": "Non-neural methods such as trees, kernels, or linear models.",
        "other": "Another architecture, or the paper does not propose a model.",
    },
)

ATTRIBUTE_QUESTIONS: dict[str, Noul | Choice] = {
    "code_released": CODE_RELEASED,
    "task_type": TASK_TYPE,
    "model_family": MODEL_FAMILY,
}
