# Arxivian -- User Stories

**Companion to:** `docs/product/feed-prd.md`
**Last updated:** 2026-09-20 (chat-first epics removed; pivot epics not re-audited)

> **Status.** Planning record for the feed pivot. SCORE-1..5, FEED-DIGEST, ONBOARD,
> LIFECYCLE and SCOPED-CHAT shipped in Phases 1-3 (SPE-269..299); SCORE-6 (code gap) is
> v1.1. The chat-first beta epics (CHAT, CITE, FEED, OPS, PERF) were removed 2026-09-20
> and are in git history. `AGENTS.md` is the description of the code as built.

Stories are grouped by epic. Each story uses MoSCoW priority (Must/Should/Could) and
references the backend/frontend files that need changes.

---

## Pivot Epics (feed model -- see `feed-prd.md`, `docs/design/scoring-pipeline.md`)

### Epic: SCORE -- Scoring Pipeline

The new backbone. Two-stage triage + scoring producing evidence-backed sub-scores. Full
design in `docs/design/scoring-pipeline.md`.

- **SCORE-1 (Must):** Stage 1 cheap triage batch task (`tasks/triage_tasks.py`) --
  metadata-only crawl, batched-abstract classification on the cheap model, survivors
  enqueue Stage 2. AC: 70-80% eliminated; no PDF download in Stage 1; deterministic task
  IDs.
- **SCORE-2 (Must):** Stage 2 scoring graph (`services/scoring_service/`) -- fan-out/fan-in
  DAG over the **4 v1 rubric dimensions** (method clarity, resource feasibility, data
  availability, demand; code gap deferred to v1.1); persists `paper_scores` +
  `score_evidence` with global sub-scores only. AC: each dimension carries quoted evidence;
  the three judged dimensions are TypeSafe Jev questions combined in code (rubric v2);
  demand is Semantic Scholar.
- **SCORE-3 (Must):** `semantic_scholar_client` (backoff-aware + net-new Redis cache) and
  its `SemanticScholarTool` `BaseTool` wrapper, reusable by the scoped chat agent. AC:
  demand from citation velocity; rate-limit/backoff path covered. (v1's only external API.)
- **SCORE-4 (Must):** `build_digest_task` -> `digests` cached candidate ranking snapshot;
  read-time user-weighted composite + compute-profile match. AC: past weeks render without
  recomputation.
- **SCORE-5 (Should):** Golden-set scoring eval (`tests/evals/integration/test_scoring_eval.py`,
  `@pytest.mark.inteval`, run by hand). AC: >=85% agreement on the implementable gate;
  calibration report; re-run before any rubric change ships.
- **SCORE-6 (v1.1):** Code-gap dimension -- `github_client` (backoff-aware + Redis cache) +
  `GithubSearchTool` + `score_code_gap` node, gated on the Phase 4 code-gap recall
  spike (script removed in SPE-297; seed in `backend/tests/evals/fixtures`). AC: searches arXiv ID + title variants + author repos; raw hits surfaced as
  evidence with an "as of `<date>`" stamp; ships unweighted first, then promoted to the
  highest-weighted signal; add code-gap agreement to the eval gate.

### Epic: FEED-DIGEST -- Weekly Ranked Feed

- **FEED-DIGEST-1 (Must):** Home feed of ranked paper cards for the current week (verdict
  line primary, score secondary, signal chips, Save/Dismiss/Implementing actions). AC:
  fully triageable from cards alone; dismiss is one action, no confirmation.
- **FEED-DIGEST-2 (Must):** Filter bar (category, minimum score) + week selector for past
  digests. AC: historical browsing hits cached digests. (The "no existing code only" filter
  arrives in v1.1 with the code-gap signal -- see SCORE-6.)

### Epic: ONBOARD -- Onboarding Profile

- **ONBOARD-1 (Must):** One-time post-sign-in flow -- select arXiv categories, declare
  compute reality (laptop / single GPU / cloud budget), optional interest keywords; stored
  on the `preferences` JSONB column on the `users` model. AC: ~30s; shapes the first digest;
  reuses the JSON path read by `scheduled_tasks.py::daily_ingest_task`.

### Epic: LIFECYCLE -- Paper Lifecycle States

- **LIFECYCLE-1 (Must):** Per-user states saved / dismissed / implementing / shipped in
  `user_paper_states` (repo URL on shipped; dismissal reason optional). AC: dismissals
  double as labeled feedback.
- **LIFECYCLE-2 (Must):** Library grouped by state; shipped items show the linked repo.
  (Shipped in SPE-296: `GET /users/me/library`, `frontend/src/pages/LibraryPage.tsx`.)

### Epic: SCOPED-CHAT -- Per-Paper Chat Panel

- **SCOPED-CHAT-1 (Must):** Chat on paper detail, pre-loaded with the paper's ingested
  content, seeded prompts ("Explain the core method," "What would a minimal repo look
  like," "What are the risky parts to reproduce"). Reuses the existing streaming + citation
  UI with a narrowed context and the `semantic_scholar` tool (the `github_search` tool joins
  in v1.1). AC: no global chat tab; conversation history list removed (data archived).
