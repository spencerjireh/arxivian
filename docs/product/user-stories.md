# Arxivian -- User Stories

**Companion to:** `docs/product/feed-prd.md`
**Last updated:** 2026-09-22 (PUBLIC epic added; ONBOARD-1 gate superseded)

> **Status.** Planning record for the feed pivot. SCORE-1..5, FEED-DIGEST, ONBOARD,
> LIFECYCLE and SCOPED-CHAT shipped in Phases 1-3 (SPE-269..299); PUBLIC (the public
> feed, `feed-prd.md` 1.1-public) is in progress; SCORE-6 (code gap) is v1.1. The
> chat-first beta epics (CHAT, CITE, FEED, OPS, PERF) were removed 2026-09-20 and are in
> git history. `AGENTS.md` is the description of the code as built.

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
  reuses the JSON path read by `scheduled_tasks.py::daily_ingest_task`. *The forced gate is
  superseded by PUBLIC-5; the form and its storage are unchanged.*

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

### Epic: PUBLIC -- Public Feed and Presentation (`feed-prd.md` 1.1-public)

The issue and paper detail are readable without an account; the account layer is
personalization. Cards and detail stop exposing pipeline internals.

- **PUBLIC-1 (Must):** Backend public reads. `GET /feed` and `GET /papers/{arxiv_id}/score`
  accept an absent bearer token (`CurrentUserOptional`); a present-but-invalid token is
  still 401. Anonymous callers get the global digest with default weights, no state and
  no profile match. `FeedItem` and the detail response carry `headline` (attribute
  template) and `meta` (ordered truthy phrases) instead of `verdict` and `signals`, plus a
  top-level `compute_match`. An unscored paper answers 202 with the paper metadata
  (`paper.abstract` included); an anonymous request never enqueues `score_paper_task`,
  takes the lock or counts against a budget. A paper unknown to the index is fetched from
  arXiv on read and stored as a metadata-only row that ingest later fills in place.
  Versioned ids (`...v2`) resolve to the stored row. AC: anonymous 200/202 tests, invalid
  token 401, unknown id 404, arXiv outage 503 with nothing enqueued; ingest fills a
  `pdf_processed=False` row; no migration.
- **PUBLIC-2 (Must):** Frontend shell and routes. The issue is `/` (`/feed` redirects with
  its query string); the landing page moves to `/about`; one top nav for everyone (Feed,
  About, Pricing; Library, Settings and the account menu when signed in; Sign in
  otherwise); the sidebar, its store and the "Beta" tag are deleted; pages become
  document-style columns. The auth session moves above the router so signed-in readers
  get a token and `/users/me` on public routes and anonymous readers never call it; a
  401 signs out only when the request carried a token. Sign-in and OAuth return to the
  page the reader came from (`state.from`, validated), default `/`. AC: route table
  tests; anonymous never fetches `/users/me`; return path round-trips through OAuth.
- **PUBLIC-3 (Must):** Cards. Headline, meta line (joined with a separator; "Fits your
  compute" appended when `compute_match`), a four-dimension meter built from the 0-100
  sub-scores with a hollow "not available" segment for null, Save + Dismiss for signed-in
  readers, a Save that opens sign-in for anonymous readers. Implementing and Shipped move
  to detail and Library. Masthead on the issue; the dismissed toggle only when signed in.
  AC: no composite number, band text or confidence icon on a card; meter segments expose
  `role="meter"` values; anonymous cards show no Dismiss.
- **PUBLIC-4 (Must):** Paper detail. Headline, meta and meter on top; four dimensions
  open by default with a band word (Strong / Mixed / Weak; Pass / Fail), level label,
  reason and evidence; a collapsed "Scoring details" section with distributions,
  judgments with probabilities, confidence and rubric version. Anonymous readers get a
  sign-in prompt in place of the chat panel, and on an unscored paper the metadata and
  abstract with "Sign in to score this paper" (no polling). AC: `<details>` closed by
  default; no `useChat` mount for anonymous readers; `usePaperScore` does not poll when
  anonymous.
- **PUBLIC-5 (Must):** Onboarding prompt. The gate is removed; a signed-in reader with
  `onboarded === false` sees a dismissible prompt at the top of the issue linking to the
  profile form; dismissal is remembered per browser. AC: prompt hidden after dismissal
  and after the profile is saved; `/onboarding` still redirects an onboarded user to `/`.
- **PUBLIC-6 (Should):** Docs. PRD 1.1-public, this file, the read-path paragraphs in
  `scoring-pipeline.md`, README and the privacy policy's anonymous-visitor paragraph.
- **PUBLIC-7 (Could, follow-ups):** written one-liner at score time; viewer-keyed feed
  queries so anonymous first paint does not wait on Clerk; link previews for public pages;
  new judged attributes for the headline.
