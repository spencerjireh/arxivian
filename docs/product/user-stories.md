# Arxivian Beta -- User Stories

**Companion to:** `docs/product/beta-prd.md` and `docs/product/feed-prd.md` (the pivot)
**Last updated:** 2026-07-16

Stories are grouped by epic. Each story uses MoSCoW priority (Must/Should/Could) and
references the backend/frontend files that need changes.

> **Pivot note.** Epics below the divider (CHAT / CITE / FEED / LIB) are chat-first beta
> work. Under the feed pivot (`feed-prd.md`) they are reframed: CHAT/CITE apply only to
> the scoped per-paper chat panel; FEED (thumbs) is deprecated in favor of card
> save/dismiss signals; LIB folds into the new LIFECYCLE epic. OPS and PERF are
> pivot-agnostic infra and carry forward unchanged. The **new pivot epics** (FEED-DIGEST,
> SCORE, ONBOARD, LIFECYCLE, SCOPED-CHAT) are defined first, below.

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
  the 2 LLM dimensions route to the stronger model via an explicit `model=` override.
- **SCORE-3 (Must):** `semantic_scholar_client` (backoff-aware + net-new Redis cache) and
  its `SemanticScholarTool` `BaseTool` wrapper, reusable by the scoped chat agent. AC:
  demand from citation velocity; rate-limit/backoff path covered. (v1's only external API.)
- **SCORE-4 (Must):** `build_digest_task` -> `digests` cached candidate ranking snapshot;
  read-time user-weighted composite + compute-profile match. AC: past weeks render without
  recomputation.
- **SCORE-5 (Should):** Golden-set eval (30-50 labeled papers) in the `@pytest.mark.eval`
  CI profile. AC: >=85% agreement on feasibility; no regression. Prerequisite, not a
  follow-on -- the labeled set gates trusting the cheap LLM dimensions.
- **SCORE-6 (v1.1):** Code-gap dimension -- `github_client` (backoff-aware + Redis cache) +
  `GithubSearchTool` + `score_code_gap` node, gated on the `spikes/github-code-gap/` recall
  spike. AC: searches arXiv ID + title variants + author repos; raw hits surfaced as
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
  (Supersedes LIB-1's read-only detail modal.)

### Epic: SCOPED-CHAT -- Per-Paper Chat Panel

- **SCOPED-CHAT-1 (Must):** Chat on paper detail, pre-loaded with the paper's ingested
  content, seeded prompts ("Explain the core method," "What would a minimal repo look
  like," "What are the risky parts to reproduce"). Reuses the existing streaming + citation
  UI with a narrowed context and the `semantic_scholar` tool (the `github_search` tool joins
  in v1.1). AC: no global chat tab; conversation history list removed (data archived).

---

## Beta Epics (chat-first -- reframed by the pivot; see pivot note above)

---

## Epic: CHAT -- Chat Experience Polish

Improve the chat UX for beta readiness. Focus on error communication and usage
awareness.

### CHAT-1: Rate limit approaching indicator

**Priority:** Should
**As a** free-tier researcher,
**I want** to see how many chats I have remaining today,
**so that** I can pace my usage and not be surprised by a hard block.

**Acceptance criteria:**

- [ ] Chat input area shows remaining chats (e.g. "3 / 20 remaining today") when the
  user is on the free tier
- [ ] Counter updates after each successful chat request
- [ ] When 5 or fewer chats remain, the indicator shifts to a warning style (amber text
  or similar)
- [ ] When 0 remain, the input is disabled with a clear message explaining the daily
  reset
- [ ] Pro tier users see no counter (unlimited)
- [ ] Data sourced from `GET /users/me` response (`chats_used_today`,
  `daily_chat_limit`)

**Implementation notes:**

- `userStore` already fetches `/users/me` after each chat. The `MeResponse` type
  already has `daily_chat_limit` and `chats_used_today` fields.
- Display logic goes in or near the chat input component.

**Files likely touched:**
- `frontend/src/components/chat/ChatInput.tsx` (or equivalent input component)
- `frontend/src/stores/userStore.ts` (already has the data)

---

### CHAT-2: Improved error messages for failed queries

**Priority:** Should
**As a** researcher,
**I want** clear, actionable error messages when my query fails,
**so that** I know what went wrong and what to try next.

**Acceptance criteria:**

- [ ] Network errors show "Connection lost. Check your internet and try again."
- [ ] Rate limit errors (HTTP 429 or backend rate limit response) show
  "Daily chat limit reached. Resets at midnight UTC."
- [ ] Timeout errors show "Response took too long. Try a simpler query or try again."
- [ ] Agent errors (ERROR SSE event) display the error message from the backend, not a
  generic fallback
- [ ] All error states are dismissible and do not block the input for subsequent queries
  (except rate limit exhaustion)

**Implementation notes:**

- The SSE handler already receives ERROR events with `error` and `code` fields.
  Currently these surface as a generic message. Map `code` values to user-friendly copy.
- Backend error codes: check `StreamEventType.ERROR` usage in the streaming router.

**Files likely touched:**
- `frontend/src/hooks/useChat.ts` (error handling in SSE handler)
- `frontend/src/stores/chatStore.ts` (error state)
- `frontend/src/components/chat/` (error display component)

---

## Epic: CITE -- Citation Explorer

Enhance how citations surface in the chat experience. The `explore_citations` backend
tool already returns structured reference data. The gap is on the frontend: citation
results appear as plain text in the agent response with no structured rendering.

### CITE-1: Structured citation rendering in chat

**Priority:** Must
**As a** researcher,
**I want** citation results to render as structured, scannable cards in the chat,
**so that** I can quickly evaluate which references are worth pursuing.

**Acceptance criteria:**

- [ ] When the agent uses `explore_citations`, the response includes a dedicated
  citation block (not just inline text)
- [ ] Each citation shows: title, authors (truncated), arXiv ID (linked to arXiv abs
  page), and whether it exists in the knowledge base
- [ ] Citations that are already ingested show a "In library" badge; others show
  "Not ingested"
- [ ] Clicking an ingested citation's title navigates to or opens its paper detail view
  (see LIB-1)
- [ ] The citation block is collapsible if there are more than 5 references

**Implementation notes:**

- `ExploreCitationsTool.execute()` returns `data.references` (list of reference
  strings parsed from PDF) and `data.reference_count`. The references are raw strings
  extracted from the PDF bibliography, not structured objects with arxiv_ids.
- This means the frontend rendering may need the agent's generation to contextualize
  the references, or the backend tool needs enhancement to cross-reference references
  against the papers table.
- Consider: should the tool attempt to match reference strings to known papers in the
  DB? This would make the "In library" badge feasible. Alternatively, the agent's
  generation prompt can be updated to format references with available metadata.

**Backend files (if enhancing the tool):**
- `backend/src/services/agent_service/tools/explore_citations.py`
- `backend/src/repositories/paper_repository.py` (add fuzzy title matching query)

**Frontend files:**
- New component: `frontend/src/components/chat/CitationBlock.tsx`
- `frontend/src/components/chat/` (message renderer to detect citation tool output)

---

### CITE-2: "Explore citations" as a suggested follow-up

**Priority:** Should
**As a** researcher who just asked about a paper,
**I want** the agent to suggest exploring that paper's citations as a follow-up action,
**so that** citation exploration feels like a natural part of the conversation flow.

**Acceptance criteria:**

- [ ] After the agent discusses a specific ingested paper, a suggestion chip appears:
  "Explore citations of [paper title]"
- [ ] Clicking the chip sends the appropriate query to trigger the `explore_citations`
  tool
- [ ] Suggestion only appears for papers that are ingested and processed (pdf_processed
  = true)

**Implementation notes:**

- The sources data in METADATA events already includes `arxiv_id` for cited papers.
  The suggestion chip can be generated client-side when sources are present.
- This is a frontend-only change. The agent will naturally use `explore_citations` when
  asked.

**Files likely touched:**
- `frontend/src/components/chat/` (suggestion chips component)
- `frontend/src/stores/chatStore.ts` (derive suggestion from latest metadata/sources)

---

## Epic: LIB -- Paper Library Enhancement

Elevate the library from a basic grid to a core feature. The backend already serves
full paper detail via `GET /papers/{arxiv_id}` including `raw_text`, `sections`,
and `references`.

### LIB-1: Paper detail view

**Priority:** Must
**As a** researcher browsing the library,
**I want** to click a paper card and see its full details,
**so that** I can read the abstract, see all authors, check sections, and access the
PDF without leaving the app.

**Acceptance criteria:**

- [ ] Clicking a paper card opens a detail view (modal or slide-over panel)
- [ ] Detail view shows:
  - Full title
  - All authors (not truncated)
  - Full abstract
  - arXiv ID (linked to arXiv abstract page)
  - Categories as tags
  - Published date
  - Processing status and date
  - Sections list (if available from PDF parsing)
  - Reference count
  - Link to open PDF
- [ ] Detail view loads data from `GET /papers/{arxiv_id}` endpoint
- [ ] Loading state while fetching (skeleton or spinner)
- [ ] Close via X button, Escape key, or clicking outside
- [ ] URL updates to `/library/{arxiv_id}` so the detail view is shareable/bookmarkable
  (optional enhancement)

**Implementation notes:**

- `PaperResponse` schema already includes `raw_text`, `sections`, and all metadata.
  The `PaperListItem` in the grid does not include `raw_text` or `references`, so
  a separate fetch to the detail endpoint is needed.
- `sections` is `list[dict] | None` -- inspect the actual shape stored by the PDF
  parser to determine what to render (likely `{name, content}` or similar).

**Frontend files:**
- New component: `frontend/src/components/library/PaperDetailModal.tsx`
- `frontend/src/components/library/PaperCard.tsx` (add click handler)
- `frontend/src/api/` (add `getPaper(arxivId)` function if not present)
- `frontend/src/types/api.ts` (ensure `PaperResponse` type includes detail fields)

**Backend:** No changes needed. Endpoint exists.

---

## Epic: FEED -- In-App Feedback

Wire the existing Langfuse feedback backend to a frontend UI. The backend
(`POST /feedback`) accepts `trace_id`, `score` (0-1), and optional `comment`.
The `trace_id` is already available in the METADATA SSE event.

### FEED-1: Thumbs up/down on agent responses

**Priority:** Must
**As a** researcher,
**I want** to rate agent responses with thumbs up or thumbs down,
**so that** I can signal response quality and help improve the system.

**Acceptance criteria:**

- [ ] Each completed agent response shows thumbs up / thumbs down buttons below the
  message
- [ ] Buttons appear only after streaming completes (not during)
- [ ] Clicking thumbs up sends `POST /feedback` with `score: 1`, clicking thumbs down
  sends `score: 0`
- [ ] The `trace_id` is taken from the message's `metadata.session_id` or the Langfuse
  trace ID if available in metadata (check what the backend actually sends in the
  METADATA event)
- [ ] After submitting, the selected button stays highlighted and both become
  non-interactive (no double-submit)
- [ ] Feedback state persists for the session (re-opening a conversation shows which
  responses were rated)
- [ ] If Langfuse is not enabled (feedback POST returns `success: false`), buttons are
  hidden or gracefully degraded

**Implementation notes:**

- The METADATA SSE event currently includes fields like `session_id`, `model`,
  `execution_time_ms`, etc. Verify whether `trace_id` is included. If not, the backend
  streaming router needs to add it to the metadata payload.
- Feedback state can be stored per-message in `chatStore` or in a separate lightweight
  store. It does not need backend persistence beyond the Langfuse score -- if the user
  reloads, losing the highlight state is acceptable for beta.

**Backend files (if trace_id not in metadata):**
- `backend/src/routers/streaming.py` (add `trace_id` to METADATA event data)

**Frontend files:**
- New component: `frontend/src/components/chat/FeedbackButtons.tsx`
- `frontend/src/api/` (add `submitFeedback()` function)
- `frontend/src/types/api.ts` (add `FeedbackRequest`/`FeedbackResponse` types)
- Message component (integrate feedback buttons)

---

### FEED-2: Bug report button

**Priority:** Must
**As a** beta tester,
**I want** a persistent bug report button in the app,
**so that** I can quickly report issues without leaving the product.

**Acceptance criteria:**

- [ ] A small, unobtrusive "Report bug" button is accessible from the main layout
  (e.g. bottom of sidebar, or a floating action)
- [ ] Clicking opens a minimal form: text description (required), optional screenshot
  upload
- [ ] On submit, sends `POST /feedback` with `score: 0`, the description as `comment`,
  and `trace_id` of the most recent conversation turn (if available) or a sentinel
  value like `"bug-report"`
- [ ] Shows a confirmation toast on success
- [ ] Form validates: description must be non-empty and under 1000 characters

**Implementation notes:**

- Reuse the same `POST /feedback` endpoint. A `trace_id` of `"bug-report"` (or similar
  convention) distinguishes bug reports from response ratings in Langfuse.
- Alternatively, if you want richer bug reporting later, this could link to an external
  form. But for beta, the Langfuse approach keeps it simple and in-house.

**Frontend files:**
- New component: `frontend/src/components/common/BugReportButton.tsx`
- Layout component (add button to sidebar or main layout)

---

## Epic: OPS -- Operational Hardening

Minimum hardening for a public-facing beta on a VPS with Coolify + Cloudflare.

### OPS-1: Sentry error tracking -- backend

**Priority:** Must
**As a** developer,
**I want** unhandled exceptions in the backend automatically reported to Sentry,
**so that** I can detect and fix production issues before users report them.

**Acceptance criteria:**

- [ ] `sentry-sdk[fastapi]` added to backend dependencies
- [ ] Sentry DSN configured via `SENTRY_DSN` environment variable (empty = disabled)
- [ ] Sentry initialized in `src/main.py` lifespan or at module level with:
  - Environment tag (`development`, `production`)
  - Release version from app config
  - Traces sample rate configurable via env var (default 0.1 for beta)
- [ ] FastAPI integration captures unhandled exceptions with request context
- [ ] Celery integration captures task failures
- [ ] Sensitive data scrubbed (auth tokens, API keys not sent to Sentry)
- [ ] `SENTRY_DSN` added to `.env.example` with comment

**Implementation notes:**

- Sentry's FastAPI integration auto-instruments. For Celery, use
  `sentry_sdk.integrations.celery.CeleryIntegration`.
- Keep Langfuse for LLM-specific tracing, Sentry for application errors. They serve
  different purposes and should coexist.

**Files likely touched:**
- `backend/pyproject.toml` (add `sentry-sdk[fastapi]`)
- `backend/src/main.py` (init Sentry)
- `backend/src/config.py` (add `sentry_dsn`, `sentry_traces_sample_rate`,
  `sentry_environment` settings)
- `backend/src/tasks/` (Celery Sentry integration)
- `backend/.env.example`

---

### OPS-2: Sentry error tracking -- frontend

**Priority:** Must
**As a** developer,
**I want** frontend JavaScript errors and unhandled promise rejections reported to
Sentry,
**so that** I can catch UI bugs that users encounter.

**Acceptance criteria:**

- [ ] `@sentry/react` added to frontend dependencies
- [ ] Sentry DSN configured via `VITE_SENTRY_DSN` environment variable (empty =
  disabled)
- [ ] Sentry initialized in `main.tsx` with:
  - Environment and release tags
  - React Router integration for route-level error tracking
  - Replay sample rate (optional, 0 by default for beta)
- [ ] Error boundaries integrated with `Sentry.ErrorBoundary` or manual
  `captureException` calls
- [ ] User context set after Clerk auth (user ID, email) so errors are attributable
- [ ] Source maps uploaded to Sentry (via build step or Sentry CLI) for readable
  stack traces
- [ ] `VITE_SENTRY_DSN` added to `frontend/.env.example`

**Files likely touched:**
- `frontend/package.json` (add `@sentry/react`)
- `frontend/src/main.tsx` (init Sentry)
- `frontend/.env.example`
- `frontend/vite.config.ts` (source map upload plugin, if using)

---

### OPS-3: Global rate limiting (per-IP)

**Priority:** Must
**As a** system operator,
**I want** per-IP request throttling on the API,
**so that** a single abusive client cannot overwhelm the service.

**Acceptance criteria:**

- [ ] Rate limiting middleware applied globally to the FastAPI app
- [ ] Default limits: 60 requests/minute per IP for general endpoints,
  10 requests/minute per IP for `/stream` (expensive LLM calls)
- [ ] Limits configurable via environment variables (`RATE_LIMIT_GENERAL`,
  `RATE_LIMIT_STREAM`)
- [ ] Returns HTTP 429 with a `Retry-After` header when limit exceeded
- [ ] Rate limit state stored in Redis (DB 2, the general cache) for consistency across
  restarts
- [ ] Health check endpoint (`/api/v1/health`) is exempt from rate limiting
- [ ] Works behind Cloudflare: reads real client IP from `CF-Connecting-IP` or
  `X-Forwarded-For` header

**Implementation notes:**

- Consider `slowapi` (built on `limits`, FastAPI-native) or a custom middleware using
  Redis INCR + EXPIRE (sliding window). `slowapi` is simpler to set up but less
  flexible.
- Cloudflare already provides basic DDoS protection at the edge. This is a second layer
  for application-level abuse (e.g. a user scripting excessive API calls).

**Files likely touched:**
- `backend/pyproject.toml` (add `slowapi` or implement custom)
- `backend/src/middleware/rate_limiting.py` (new)
- `backend/src/main.py` (register middleware)
- `backend/src/config.py` (add rate limit settings)
- `backend/.env.example`

---

## Epic: PERF -- Backend Optimization

Based on the existing design document at
`docs/redis-embedding-cache-ingestion-lock.md`. These reduce API costs and prevent
redundant work.

### PERF-1: Redis embedding cache

**Priority:** Should
**As a** system operator,
**I want** embedding API calls cached in Redis,
**so that** repeated queries and re-ingestion don't burn Jina API credits.

**Acceptance criteria:**

- [ ] `JinaEmbeddingsClient.embed_query()` checks Redis before calling the Jina API
- [ ] Cache key format: `embed:{model}:{sha256(text)}`
- [ ] Cache TTL: 48 hours (configurable via `EMBEDDING_CACHE_TTL` env var)
- [ ] Cache hit returns the stored embedding vector directly (deserialized from Redis)
- [ ] Cache miss calls Jina, stores result, returns it
- [ ] If Redis is unavailable, falls back to direct API call (no crash)
- [ ] `embed_documents()` (batch) also uses the cache per-document
- [ ] Metrics: log cache hit/miss counts at DEBUG level

**Implementation notes:**

- See `docs/redis-embedding-cache-ingestion-lock.md` for the full design.
- Use Redis DB 2 (the general cache) via `app.state.redis`.
- Store embeddings as bytes (msgpack or raw float32 buffer) for space efficiency.

**Files likely touched:**
- `backend/src/clients/embeddings_client.py`
- `backend/src/factories/client_factories.py` (inject Redis into client)
- `backend/src/config.py` (add `embedding_cache_ttl` setting)
- `backend/.env.example`

---

### PERF-2: Redis ingestion lock

**Priority:** Should
**As a** system operator,
**I want** concurrent ingestion of the same paper to be deduplicated,
**so that** multiple users requesting the same paper don't trigger parallel downloads
and processing.

**Acceptance criteria:**

- [ ] Before starting ingestion, acquire a Redis lock:
  `SET ingest_lock:{arxiv_id} NX EX 600`
- [ ] If lock acquired, proceed with ingestion normally
- [ ] If lock not acquired (another worker is processing), return early with a message
  like "Paper is already being ingested" rather than failing
- [ ] Lock TTL matches `CELERY_TASK_TIMEOUT` (default 600s) to auto-expire on
  worker crash
- [ ] Lock released explicitly on successful completion (not just TTL expiry)
- [ ] If Redis is unavailable, skip locking and proceed (graceful degradation)
- [ ] Celery task returns a distinct status ("already_processing") so the caller knows
  what happened

**Implementation notes:**

- See `docs/redis-embedding-cache-ingestion-lock.md` for the full design.
- Use Redis DB 2 via injected client.

**Files likely touched:**
- `backend/src/services/ingest_service.py`
- `backend/src/factories/service_factories.py` (inject Redis)
- `backend/src/tasks/ingest_tasks.py`
- `backend/src/dependencies.py`

---

## Priority Summary

| ID | Story | Priority | Epic |
|----|-------|----------|------|
| FEED-1 | Thumbs up/down on responses | Must | FEED |
| FEED-2 | Bug report button | Must | FEED |
| CITE-1 | Structured citation rendering | Must | CITE |
| LIB-1  | Paper detail view | Must | LIB |
| OPS-1  | Sentry backend | Must | OPS |
| OPS-2  | Sentry frontend | Must | OPS |
| OPS-3  | Global rate limiting | Must | OPS |
| CHAT-1 | Rate limit indicator | Should | CHAT |
| CHAT-2 | Improved error messages | Should | CHAT |
| CITE-2 | Citation follow-up suggestions | Should | CITE |
| PERF-1 | Embedding cache | Should | PERF |
| PERF-2 | Ingestion lock | Should | PERF |

### Suggested implementation order

The order balances quick wins, dependency chains, and user-visible impact:

```
Phase 1 -- Foundation (do first, unblocks everything)
  OPS-1  Sentry backend        (catch errors from day one)
  OPS-2  Sentry frontend       (catch errors from day one)
  OPS-3  Global rate limiting   (protect the service before opening up)

Phase 2 -- Core UX gaps (the "must" user-facing features)
  FEED-1 Thumbs up/down        (quick win, high signal for quality)
  FEED-2 Bug report button     (beta users need a way to report issues)
  LIB-1  Paper detail view     (library becomes a real feature)
  CITE-1 Citation rendering    (fulfills the landing page promise)

Phase 3 -- Polish and optimization (should-haves)
  CHAT-1 Rate limit indicator  (UX improvement for free tier)
  CHAT-2 Error messages        (reduces support burden)
  CITE-2 Citation suggestions  (engagement improvement)
  PERF-1 Embedding cache       (cost reduction)
  PERF-2 Ingestion lock        (operational safety)
```

---

## Glossary

| Term | Meaning |
|---|---|
| **Communal knowledge base** | All ingested papers are shared across all users. No per-user paper silos. |
| **RRF** | Reciprocal Rank Fusion -- combines vector and full-text search rankings. |
| **Guardrail** | First node in the agent workflow. Scores query relevance 0-100 and rejects off-topic queries. |
| **Trace ID** | Langfuse identifier linking all LLM calls in a single agent execution. Used for feedback attribution. |
| **Coolify** | Self-hosted PaaS (like Heroku) running on the VPS. Handles deployment, SSL, and process management. |
