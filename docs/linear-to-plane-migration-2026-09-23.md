# Linear -> Plane migration (2026-09-23)

On 2026-09-23 the Arxivian tracker moved from Linear (project *Arxivian — Feed Pivot*,
team `SPE`) to the self-hosted **Plane** instance: workspace `workspace-1`, project
**Arxivian**, key **`ARX`** —
[open the project](https://plane.spencerjireh.com/workspace-1/projects/d8aa527c-3f59-4525-a9bc-ffafdf30b496).
Arxivian was the last of the trackers still on Linear; Boyage moved the same way on
2026-07-30.

## Conventions

- **Issue ids are `ARX-N`.** Every in-repo `SPE-N` marker was rewritten to its `ARX-N`
  equivalent in the migration commit, so the working tree names only Plane ids.
- **Git history still says `SPE-N`.** Commit subjects merged before 2026-09-23 carry the
  old id and cannot be rewritten. The table below is how you resolve them. Merged PR
  titles on GitHub are likewise unchanged.
- The mapping is a formula, not a lookup — work items were created in ascending SPE order,
  so a parent always precedes its children:
  - `SPE-265..277` -> `ARX-1..13`  (`ARX = SPE - 264`)
  - `SPE-281..318` -> `ARX-14..51` (`ARX = SPE - 267`)
- `SPE-278`, `SPE-279` and `SPE-280` fall inside that range but belong to a different
  project (*nthtime*) and were not migrated.
- Each migrated work item opens with a `Migrated from Linear SPE-N · created … · state at
  migration …` header and carries `external_source="linear"` / `external_id="SPE-N"` in the
  API, so an old id is machine-resolvable without this file.
- Linear **milestones** became Plane **modules** (the same five phases). Epics carry over as
  plain parent/child nesting — ARX-19 parents ARX-20..27 — because this Plane build has no
  work-item types. `In Review` was added to Plane's default state set.
- Linear **comments were not migrated**. Merged and open **PRs are attached as links** on the
  work item that references them.
- The Linear workspace stays as a **read-only archive**; `linear.app` URLs in older documents
  are deliberately left as historical links.

## The 51 migrated work items

| Linear | Plane | State at migration | PRs | Title |
|---|---|---|---|---|
| SPE-265 | ARX-1 | Done | — | Label golden set on the 4 v1 dimensions (30–50 papers) |
| SPE-266 | ARX-2 | Done | — | Author rubric anchors + evidence-extraction prompts (4 v1 dimensions) |
| SPE-267 | ARX-3 | Done | #4 | DB schema + Alembic migration: paper_scores, score_evidence, user_paper_states, digests |
| SPE-268 | ARX-4 | Done | #7 | SCORE-1: Stage 1 cheap triage batch task |
| SPE-269 | ARX-5 | Done | #9 | SCORE-3: Semantic Scholar client + SemanticScholarTool |
| SPE-270 | ARX-6 | Done | #11 | SCORE-2: Stage 2 scoring graph (4-dimension fan-out/fan-in) |
| SPE-271 | ARX-7 | Done | #13 | SCORE-4: build_digest_task + cached digest snapshot |
| SPE-272 | ARX-8 | Done | #12 | SCORE-5: Wire golden-set eval gate in CI (@pytest.mark.eval) |
| SPE-273 | ARX-9 | Done | #21 | ONBOARD-1: Onboarding profile flow |
| SPE-274 | ARX-10 | Done | #18 | FEED-DIGEST-1: Home feed of ranked paper cards |
| SPE-275 | ARX-11 | Done | #20 | FEED-DIGEST-2: Filter bar + week selector |
| SPE-276 | ARX-12 | Done | #19 | Paper detail: score breakdown + evidence |
| SPE-277 | ARX-13 | Done | #22 | SCOPED-CHAT-1: Per-paper scoped chat panel |
| SPE-281 | ARX-14 | Done | #10 | Migrate all LLM calls to openai/gpt-5-nano + reasoning-model client compat |
| SPE-282 | ARX-15 | Done | #14 | Runtime env missing openai/gpt-5-nano in ALLOWED_LLM_MODELS after ARX-14 (blocks all LLM calls) |
| SPE-283 | ARX-16 | Done | — | arXiv crawl over-fetches + scoring retry-storms into 429s (rate-limit robustness) |
| SPE-284 | ARX-17 | Done | #23 #17 | Semantic Scholar demand soft-fails on keyless pool — set SEMANTIC_SCHOLAR_API_KEY |
| SPE-285 | ARX-18 | Backlog | — | Pre-existing: conversations.session_id is globally unique, so cross-user session collision 500s (3 failing integration tests) |
| SPE-286 | ARX-19 | Done | #15 | SCORE-6: Jev-native Stage 2 scoring (rubric v2) |
| SPE-287 | ARX-20 | Done | — | TypeSafe client, settings, factory, exceptions; remove scoring_strong_model |
| SPE-288 | ARX-21 | Done | — | Section splitter over paper.raw_text + code mentions |
| SPE-289 | ARX-22 | Done | — | Rubric v2 schemas + judgments.py combine rules |
| SPE-290 | ARX-23 | Done | — | Migration 020: paper_scores.dimensions / attributes / model / input_tokens |
| SPE-291 | ARX-24 | Done | — | Jev question set + dimension node rewrite + attributes |
| SPE-292 | ARX-25 | Done | — | Rate-limit robustness: score_paper_task retry policy + arXiv max_results cap + crawl pacing |
| SPE-293 | ARX-26 | Done | — | Eval gate v2 + calibration report |
| SPE-294 | ARX-27 | Done | — | Docs: rubric v2, scoring-pipeline, CLAUDE.md |
| SPE-295 | ARX-28 | Done | #16 | Golden-label review + compute-tier / data-access wording |
| SPE-296 | ARX-29 | Done | #45 | LIFECYCLE-2: Library grouped by lifecycle state |
| SPE-297 | ARX-30 | Done | #24 | Hygiene: dead code, stale pre-pivot docs, misnamed tests |
| SPE-298 | ARX-31 | Done | #25 | Backend: scoped-only chat agent, no per-request LLM knobs, drop chat-first leftovers |
| SPE-299 | ARX-32 | Done | #26 | Frontend: feed is home, global chat removed, scoped chat only |
| SPE-300 | ARX-33 | Done | #27 | Lint/format gate on both trees: ruff rule set incl. tests, Prettier, type-checked ESLint, knip |
| SPE-301 | ARX-34 | Done | #28 | CI hardening: integration job, coverage ratchet, docker build check, PR-title check, dependabot, branch rulesets |
| SPE-302 | ARX-35 | Done | #77 | Daily budget for on-demand scoring: global cap plus a flat per-user cap |
| SPE-303 | ARX-36 | Done | #44 | Replace Langfuse with Pydantic Logfire (OpenTelemetry) tracing |
| SPE-304 | ARX-37 | Done | #68 | Drop the unused paper_scores.details column |
| SPE-305 | ARX-38 | Done | #69 | Feed-product copy on sign-in, sign-up and pricing pages |
| SPE-306 | ARX-39 | Done | #74 | Triage drops every paper: LLM echoes arXiv:-prefixed ids that never match the crawled ids |
| SPE-307 | ARX-40 | Done | #80 | Replace Jina embeddings with OpenAI text-embedding-3-small via LiteLLM; re-embed existing chunks |
| SPE-308 | ARX-41 | Done | #82 | PUBLIC-6: Docs: public feed direction (PRD 1.1-public, stories, read path, README, privacy) |
| SPE-309 | ARX-42 | Done | #83 | PUBLIC-1: Backend: public feed and score reads, anonymous metadata-only 202, headline and meta card fields |
| SPE-310 | ARX-43 | Done | #84 | PUBLIC-2: Frontend: feed at /, top nav, /about, auth session, sign-in return path |
| SPE-311 | ARX-44 | Done | #85 | PUBLIC-3: Frontend: headline, meta line and dimension meter cards; onboarding prompt |
| SPE-312 | ARX-45 | Done | — | PUBLIC-4: Frontend: paper detail restructure, Scoring details disclosure, anonymous states |
| SPE-313 | ARX-46 | Backlog | — | PUBLIC-7: Follow-ups: written one-liner at score time, viewer-keyed feed queries, public link previews, new headline attributes |
| SPE-314 | ARX-47 | Done | #86 | Promote the public feed batch to production |
| SPE-315 | ARX-48 | Done | #87 | WEB-1: Feature folders, @/ alias and lint-enforced import boundaries (Bulletproof React) |
| SPE-316 | ARX-49 | Done | #88 | WEB-2: Frontend hygiene: lifecycle hook at the leaf, me query, self-fetching chat cache, wrappers |
| SPE-317 | ARX-50 | In Progress | #89 | WEB-3: Generate frontend API types from the FastAPI OpenAPI document |
| SPE-318 | ARX-51 | In Progress | #90 | WEB-4: Logfire browser SDK (client errors and traces in the backend's Logfire project) |

`ARX-52` is the migration itself and has no Linear ancestor.
