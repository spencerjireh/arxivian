# GitHub Code-Gap Efficacy Spike

**Status: throwaway experiment.** Not application code. Nothing here is imported by the
backend and none of it should be built on directly -- it exists to answer one question
before the scoring pipeline is built, then it can be deleted (keep `golden_papers.json`).

## The question

Code gap is the **highest-weighted** dimension in the scoring rubric
(`docs/design/scoring-pipeline.md`): "does an implementation of this paper already exist?"
The whole feed pivot leans on that signal. But whether GitHub search can actually find a
paper's known implementation is unproven -- it is an *efficacy* question, not a coding
question.

This spike measures it directly:

> Given a paper, can GitHub search surface its known repo, and with which query strategy?

If the answer is "not reliably," the code-gap signal is noise and the design needs
rethinking **before** `clients/github_client.py` and the `paper_scores` schema get built.

## Run it

```bash
# Recommended: with a token (enables code search + higher rate limit)
GITHUB_TOKEN=<your_pat> uv run spikes/github-code-gap/github_code_gap_spike.py

# Also works without a token: repo-search strategies only, ~10 req/min, code search skipped
uv run spikes/github-code-gap/github_code_gap_spike.py
```

The script is a self-contained PEP 723 uv script (declares its own `httpx` dependency
inline) -- no backend install, no `pyproject.toml` change.

### Token

A **fine-grained or classic PAT with no scopes** is enough (public search only). Create one
at GitHub -> Settings -> Developer settings -> Personal access tokens. `public_repo`
read is sufficient; no write scopes needed. The token is read from the ambient `GITHUB_TOKEN`
env var and is never written to disk.

## What it does

For each labeled paper in `golden_papers.json` it runs up to four query strategies and
records the rank at which the known repo appears (if at all):

| Strategy | Endpoint | Query | Notes |
|---|---|---|---|
| `repo_arxiv_id` | repositories | the arXiv id | repositories search does not index README bodies, so this is often weak -- that's a finding |
| `repo_title` | repositories | significant title tokens | precision drops on generic titles ("Segment Anything") |
| `repo_author` | repositories | first-author surname + top title tokens | catches author-named repos (`KaimingHe/...`) |
| `code_arxiv_id` | code | the arXiv id | **needs a token**; searches file/README contents, usually the strongest signal |

It honors GitHub's rate limits (paces requests, respects `Retry-After` /
`X-RateLimit-Reset`, backs off on 403/429) and counts rate-limit hits -- itself a data
point, since the design names external rate limits as the real throughput bottleneck.

## Reading the output

- **Per-paper table** -- rank of the known repo per strategy (`-` = not found in the top
  20). Lets you see *which* papers and *which* strategies miss.
- **Recall@k table** -- recall@1/@5/@10 per strategy and combined (best rank across
  strategies), computed only over papers labeled `has_code: true`.
- **False-signal watch** -- for papers with **no** known repo (`has_code: false`, a genuine
  code gap), the top repo-search hits. A gap should return empty or clearly-unrelated
  results; a confident-looking match here is a false positive, the exact failure mode the
  design fears most.
- **Verdict line** -- combined recall@10 vs a ~0.80 bar. Below the bar => the code-gap
  signal needs rethinking (better query strategies, PDF-reference mining, or a lower rubric
  weight) before building the client.

Full machine-readable detail is written to `results.json` (git-ignored-worthy; it is a run
artifact, not a source of truth).

## `golden_papers.json`

~20 hand-labeled papers spanning easy cases (famous official repos), hard cases (code
buried in a monorepo, author-named repos, renamed repos), and genuine gaps (prompting
techniques, closed models). **This file is the durable output of the spike** -- it seeds
the 30-50-paper eval golden set the scoring pipeline needs
(`docs/design/scoring-pipeline.md` -> Evaluation). Extend it as you go.
