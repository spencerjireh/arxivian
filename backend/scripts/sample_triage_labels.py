"""Draw a stratified, blind labelling sample from a triage candidate dump.

Reads the JSONL written by `dump_triage_candidates.py` and emits two files:

* a **labelling** file carrying only `id`, `arxiv_id`, `title` and `abstract`, shuffled, and
* a **key** file holding each row's triage verdict, sort score, stratum and stratum size.

The split is the point. A labeller who can see `keep` or `rough_implementability` is no
longer an independent judge, and every number the eval then produces measures agreement with
a verdict the labeller was shown rather than the quality of that verdict. So the two files
stay separate until the labels come back, and only then are they joined on `id`.

Sampling is stratified because the strata are wildly unequal -- roughly 140 rejected against
4200 capped in a widened crawl -- and a uniform sample would barely touch the rejects. Each
row records its stratum and that stratum's population so an overall rate can be reweighted
rather than read straight off the sample.

Usage:

    uv run python -m scripts.sample_triage_labels \\
        --dump /tmp/candidates.jsonl --labels-out /tmp/to_label.json --key-out /tmp/key.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# Defaults sized for roughly 150 papers, which is about half an hour at three-way labelling.
DEFAULT_SAMPLE = {"rejected": 40, "survived": 50, "capped": 60}
# Fixed so a re-run reproduces the same sample; change it only to draw a genuinely new one.
DEFAULT_SEED = 20261024


def _progress(message: str) -> None:
    """Progress goes to stderr so stdout stays free for redirection."""
    sys.stderr.write(message + "\n")


def _load(dump: Path) -> list[dict[str, Any]]:
    with dump.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _sample(
    rows: list[dict[str, Any]], sizes: dict[str, int], seed: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Take `sizes[stratum]` rows per outcome, returning the picks and stratum populations."""
    rng = random.Random(seed)
    populations: dict[str, int] = {}
    picked: list[dict[str, Any]] = []
    for stratum, wanted in sizes.items():
        pool = [r for r in rows if r["outcome"] == stratum]
        populations[stratum] = len(pool)
        if not pool:
            _progress(f"  warning: stratum {stratum!r} is empty, skipping")
            continue
        take = min(wanted, len(pool))
        if take < wanted:
            _progress(f"  warning: stratum {stratum!r} has only {len(pool)}, wanted {wanted}")
        picked.extend(rng.sample(pool, take))
    return picked, populations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", required=True, help="JSONL from dump_triage_candidates")
    parser.add_argument("--labels-out", required=True, help="blind labelling file (JSON)")
    parser.add_argument("--key-out", required=True, help="verdict key (JSON)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    for stratum, default in DEFAULT_SAMPLE.items():
        parser.add_argument(f"--n-{stratum}", type=int, default=default)
    args = parser.parse_args()

    rows = _load(Path(args.dump))
    _progress(f"read {len(rows)} candidates")

    sizes = {stratum: getattr(args, f"n_{stratum}") for stratum in DEFAULT_SAMPLE}
    picked, populations = _sample(rows, sizes, args.seed)

    rng = random.Random(args.seed)
    rng.shuffle(picked)

    labelling: list[dict[str, Any]] = []
    key: dict[str, Any] = {"seed": args.seed, "populations": populations, "rows": {}}
    for i, row in enumerate(picked):
        # Opaque and order-based, so the id itself leaks nothing about the stratum.
        item_id = f"p{i:03d}"
        labelling.append(
            {
                "id": item_id,
                "arxiv_id": row["arxiv_id"],
                "title": row["title"],
                "abstract": row["abstract"],
            }
        )
        key["rows"][item_id] = {
            "arxiv_id": row["arxiv_id"],
            "category": row["category"],
            "outcome": row["outcome"],
            "keep": row["keep"],
            "rough_implementability": row["rough_implementability"],
            "paper_class": row["paper_class"],
        }

    labels_out = Path(args.labels_out)
    labels_out.parent.mkdir(parents=True, exist_ok=True)
    labels_out.write_text(json.dumps(labelling, indent=2) + "\n")

    key_out = Path(args.key_out)
    key_out.parent.mkdir(parents=True, exist_ok=True)
    key_out.write_text(json.dumps(key, indent=2) + "\n")

    leaked = {k for row in labelling for k in row} - {"id", "arxiv_id", "title", "abstract"}
    if leaked:  # pragma: no cover - guards the premise of the whole exercise
        _progress(f"ERROR: labelling file leaks verdict fields: {sorted(leaked)}")
        return 1

    _progress(f"\nwrote {len(labelling)} papers to {labels_out}")
    for stratum, population in sorted(populations.items()):
        taken = sum(1 for r in key["rows"].values() if r["outcome"] == stratum)
        _progress(f"  {stratum:<12} {taken:>3} sampled of {population}")
    _progress(f"key written to {key_out} (do not open it while labelling)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
