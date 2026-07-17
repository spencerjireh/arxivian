"""Throwaway smoke check for the v1 scoring rubric prompts.

Runs the two LLM-judged dimensions (method clarity, resource feasibility) over a handful of
hand-picked papers with real method/compute excerpts, on the stronger model, and prints the
predicted band next to the golden label. Purpose: catch prompt/schema wiring problems and
gross disagreement BEFORE the Phase 1 pipeline is built. Not application code -- delete once
the scoring graph and its integration tests exist.

Run from `backend/` (needs API keys in the environment, e.g. inside the backend container):

    just shell-backend
    uv run python scripts/rubric_smoke.py

The strong model is hardcoded to `openai/gpt-4o-mini` from `allowed_llm_models`; the
`scoring_strong_model` config setting is a Phase 1 addition.
"""

from __future__ import annotations

import asyncio

from src.clients.litellm_client import LiteLLMClient
from src.schemas.scoring_state import DimensionScore, score_to_band
from src.services.scoring_service.prompts import (
    get_method_clarity_prompt,
    get_resource_feasibility_prompt,
)

STRONG_MODEL = "openai/gpt-4o-mini"

# Five papers spanning the spectrum, each with a short real excerpt so the prompts have
# something concrete to judge without the ingest pipeline. `expected_*` mirror the golden set.
SAMPLES: list[dict] = [
    {
        "arxiv_id": "2106.09685",
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "abstract": "We propose Low-Rank Adaptation, which freezes the pretrained model weights and injects trainable rank-decomposition matrices into each layer of the Transformer.",
        "spans": {
            "pseudocode": [
                "For a pretrained weight W0, constrain the update: W0 + BA, where B in R^{d x r}, A in R^{r x k}, rank r << min(d, k). Only A and B are trained; W0 is frozen. Scale BA by alpha/r.",
                "Applied to the query and value projections; r in {1,2,4,8}, alpha=16, dropout=0.1.",
            ],
            "compute": [
                "Reduces trainable parameters by 10,000x; fine-tunes GPT-3 175B with a single adapter set; experiments run on standard GPUs.",
            ],
        },
        "expected_method": "HIGH",
        "expected_resource": "HIGH",
    },
    {
        "arxiv_id": "2304.02643",
        "title": "Segment Anything",
        "abstract": "We build the largest segmentation dataset to date, with over 1 billion masks on 11M images, and train a promptable segmentation model.",
        "spans": {
            "pseudocode": [
                "The model has an MAE-pretrained ViT-H image encoder, a prompt encoder for points/boxes/masks, and a lightweight two-layer mask decoder with a bidirectional transformer.",
            ],
            "compute": [
                "The model was trained on 256 A100 GPUs. The data engine and SA-1B pipeline required substantial infrastructure.",
            ],
        },
        "expected_method": "HIGH",
        "expected_resource": "LOW",
    },
    {
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "abstract": "We propose the Transformer, a model architecture relying entirely on attention mechanisms, dispensing with recurrence and convolutions.",
        "spans": {
            "pseudocode": [
                "Scaled dot-product attention: softmax(QK^T / sqrt(d_k)) V. Multi-head with h=8 heads, d_model=512, d_ff=2048. Sinusoidal positional encodings. 6 encoder and 6 decoder layers.",
                "Adam with beta1=0.9, beta2=0.98; warmup 4000 steps; dropout 0.1; label smoothing 0.1.",
            ],
            "compute": [
                "The base model trained for 100,000 steps (~12 hours) on 8 NVIDIA P100 GPUs; the big model for 3.5 days on 8 GPUs.",
            ],
        },
        "expected_method": "HIGH",
        "expected_resource": "MED",
    },
    {
        "arxiv_id": "2204.02311",
        "title": "PaLM: Scaling Language Modeling with Pathways",
        "abstract": "We trained a 540-billion parameter, densely activated Transformer language model on 6144 TPU v4 chips using Pathways.",
        "spans": {
            "pseudocode": [
                "A standard decoder-only Transformer with modifications: SwiGLU activations, parallel attention/FFN layers, multi-query attention, RoPE embeddings. Many system details are Pathways-specific.",
            ],
            "compute": [
                "540B parameters trained on 6144 TPU v4 chips across two pods connected over data-center network.",
            ],
        },
        "expected_method": "MED",
        "expected_resource": "LOW",
    },
    {
        "arxiv_id": "2006.11239",
        "title": "Denoising Diffusion Probabilistic Models",
        "abstract": "We present high quality image synthesis results using diffusion probabilistic models trained with a weighted variational bound.",
        "spans": {
            "pseudocode": [
                "Training: sample t ~ Uniform, epsilon ~ N(0,I), take gradient step on || epsilon - epsilon_theta(sqrt(alphabar_t) x0 + sqrt(1-alphabar_t) epsilon, t) ||^2. Sampling: iteratively denoise x_t to x_{t-1}. T=1000, linear beta schedule.",
            ],
            "compute": [
                "Trained on CIFAR-10 and 256x256 LSUN; a U-Net backbone; single-GPU-days for CIFAR-scale.",
            ],
        },
        "expected_method": "HIGH",
        "expected_resource": "MED",
    },
]


async def _score(client: LiteLLMClient, builder, spans: dict, meta: dict) -> DimensionScore:
    system, user = builder(spans, meta)
    return await client.generate_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=DimensionScore,
        model=STRONG_MODEL,
    )


def _mark(predicted_band: str, expected_band: str) -> str:
    return "OK " if predicted_band == expected_band else "MISS"


async def main() -> None:
    client = LiteLLMClient(model=STRONG_MODEL, timeout=90.0)
    print(f"Rubric smoke check on {STRONG_MODEL} -- {len(SAMPLES)} papers\n")
    print(f"{'paper':28} {'dimension':22} {'pred':>4} {'band':>5} {'exp':>5}  hit")
    print("-" * 78)

    hits = 0
    total = 0
    for s in SAMPLES:
        meta = {"arxiv_id": s["arxiv_id"], "title": s["title"], "abstract": s["abstract"]}
        mc = await _score(client, get_method_clarity_prompt, s["spans"], meta)
        rf = await _score(client, get_resource_feasibility_prompt, s["spans"], meta)

        for label, result, expected in (
            ("method_clarity", mc, s["expected_method"]),
            ("resource_feasibility", rf, s["expected_resource"]),
        ):
            band = score_to_band(result.score)
            total += 1
            hits += band == expected
            print(
                f"{s['title'][:28]:28} {label:22} {result.score:>4} {band:>5} {expected:>5}  "
                f"{_mark(band, expected)}"
            )

    print("-" * 78)
    print(f"band agreement: {hits}/{total}")


if __name__ == "__main__":
    asyncio.run(main())
