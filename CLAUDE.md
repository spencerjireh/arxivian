# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arxivian -- full-stack agentic RAG system for analyzing arXiv papers. FastAPI + React + PostgreSQL/pgvector + LangGraph + Celery.

## Development Commands

All development runs in Docker via `just`. Run `just --list` for full list.

```bash
just setup              # First-time: create .env files from examples
just dev                # Build and start with hot reload
just down               # Stop services
just test               # All tests (spins up test containers)
just test tests/unit/test_file.py::test_func   # Single test
just test -k "pattern"  # Pattern match
just lint               # Ruff lint + format check on src, tests, alembic
just format             # Ruff formatter
just fix                # Auto-fix lint and format issues
just check              # Lint + typecheck
just deadcode           # vulture report (advisory, not a gate)
just eval               # Run LLM-backed evals (requires API keys)
just migrate            # Run Alembic migrations
just shell-backend      # Shell in backend container
just clean              # Stop, remove volumes + local images
just lint-frontend      # ESLint (type-checked) + knip via docker
just test-frontend      # Vitest via docker
```

CI (`.github/workflows/ci.yml`) runs seven jobs on every PR: `backend-lint` (uv lock check, ruff on src/tests/alembic, ty), `backend-test` (unit + api with the coverage gate), `backend-integration` (pgvector service container, `alembic upgrade head / downgrade -1 / upgrade head`, `tests/integration`), `frontend-lint` (eslint + knip, prettier, tsc), `frontend-test` (vitest with coverage thresholds), `docker` (coolify compose interpolation with dummy vars + production image builds for both services; the only check that exercises the relaunch path), `pr-title` (conventional-commit title; squash-merge uses it). Dependabot (`.github/dependabot.yml`) opens grouped weekly PRs for uv, npm and actions. `main` and `production` are protected by rulesets: PR required, the six CI checks required on `main`, no force-push or deletion, squash merges only.

One-time: `uvx pre-commit install` wires ruff (backend) and lint-staged (eslint + prettier on staged frontend files) into `git commit`.

Backend tools (run inside container or with `just exec-backend`):
```bash
uv run ruff check src/ tests/ alembic/   # Lint (rule set in pyproject: E,W,F,I,UP,B,SIM,RUF,PT,ARG,ERA,T20,PTH,ASYNC,PERF)
uv run ruff format src/ tests/ alembic/  # Format
uv run ty check src/          # Type check
uv run alembic upgrade head   # Run migrations
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`, `@pytest.mark.eval`, `@pytest.mark.inteval`. Test dirs mirror markers. Pytest runs with `asyncio_mode = "auto"` (session-scoped loop) and `filterwarnings = error` (new deprecations fail the run). Coverage gate: backend `fail_under = 90` (unit + api, with the `omit` list in pyproject), frontend thresholds in `vitest.config.ts`; both are ratchets -- raise when the number goes up, never lower. Integration tests use a dedicated test DB (port 5433), config in `.env.test`.

## Architecture

### Backend (`/backend/src/`)

Layered: `routers/` -> `services/` -> `repositories/` -> `models/` (async SQLAlchemy). Also: `schemas/` (Pydantic), `clients/` (LiteLLM/LLM, arXiv, Jina, Semantic Scholar, TypeSafe Jev, Langfuse; planned: GitHub), `middleware/`, `factories.py` (the one construction module for clients, services and the agent; `dependencies.py` only wires FastAPI `Depends`).

**Agent service** (`services/agent_service/`, paper-scoped only since Phase 3 / SPE-298): a LangGraph workflow compiled once without a checkpointer: classify_and_route -> executor -> evaluate_batch -> generate, plus out_of_scope; the evaluate step can loop back to classify for a rewrite up to `MAX_ITERATIONS`. Three tools (in `tools/`): retrieve_chunks (`SearchService.retrieve_within_paper`, no RRF threshold), explore_citations, semantic_scholar. SSE events: STATUS, CONTENT, SOURCES, CITATIONS, METADATA, ERROR, DONE. `POST /stream` takes `{query, arxiv_id, session_id?}` and nothing else (no per-request model or tuning; `extra="forbid"`); the scope is persisted on `conversations.paper_id` (migration 021) and wins on follow-ups (`routers/stream.py::resolve_scoped_paper`; 409 `PAPER_NOT_INGESTED` / `SCOPE_MISMATCH`). One LLM for everything: `DEFAULT_LLM_MODEL` (structured calls may use `STRUCTURED_OUTPUT_MODEL`); the other knobs live in `Settings` (`GUARDRAIL_THRESHOLD`, `DEFAULT_TOP_K`, `MAX_ITERATIONS`, `CONVERSATION_WINDOW`, `DEFAULT_TEMPERATURE`, `AGENT_TIMEOUT_SECONDS`). `GET /conversations?arxiv_id=` (required) lists a paper's threads; a session id that belongs to another user is a 403. There is no HITL ingest, no corpus search tool, no resume, no server-side cancel (the client aborts the fetch).

**Scoring service** (`services/scoring_service/`, feed pivot -- Phase 1 shipped, rubric v2): a second LangGraph workflow, a fixed fan-out/fan-in DAG (fetch_and_extract -> 4 parallel dimension nodes -> compose_and_persist) that scores papers for implementability. No streaming, no checkpointer. Judgments come from **TypeSafe Jev** (`clients/typesafe_client.py`; typed answers with calibrated probabilities, no text generation): method clarity = 4 Nouls combined by a Poisson-binomial, resource feasibility = 1 compute-tier Score + 2 aux Nouls, data availability = 1 Choice regrouped into the PASS/FAIL gate; demand = Semantic Scholar (no LLM). Questions in `questions.py`, combine rules in `judgments.py`, section state from `utils/section_splitter.py` over `paper.raw_text`. Stored shape (`schemas/scoring_state.py`): per-dimension level distribution + atomic judgments in `paper_scores.dimensions` (JSONB); the `*_score` integers are derived denormalizations. Product attributes (code released, task type, model family) in `paper_scores.attributes`. Golden set + eval gate in `tests/evals/`. See `docs/design/scoring-pipeline.md` and `docs/design/scoring-rubric.md`.

**Feed service** (`services/feed_service/`, `schemas/feed.py`, Phase 2 -- SPE-274): the read path over the cached digest. `FeedService.get_feed` batch-loads the live `papers` / `paper_scores` / `user_paper_states` rows for a digest week and derives each card in pure code: read-time composite (`compute_composite`, NULL sub-scores renormalize), compute-profile match, a template verdict line from the Jev judgments (no LLM), signal chips, and a low-confidence marker. Routers: `feed` (`GET /feed`), `paper_states` (`PUT`/`DELETE /papers/{arxiv_id}/state`, `GET /users/me/papers`), and `GET /papers/{arxiv_id}/score` in `papers.py` (SPE-276: full per-dimension breakdown with `score_evidence` spans; when the paper is not scored it enqueues `score_paper_task` behind a Redis `SET NX` lock (`score:ondemand:{arxiv_id}`, TTL `ONDEMAND_SCORE_LOCK_SECONDS`, released by the task) and answers 202 until the client's next poll finds a score). The onboarding profile (SPE-273) lives in `users.preferences["feed_profile"]` (`schemas/users.py::FeedProfile`; written by `PATCH /users/me/preferences`, read on `GET /users/me` as `preferences.feed_profile` + `onboarded`); it never touches the system user's `arxiv_searches` key. Per-user `weights` are reserved and not settable via the API.

**Celery tasks** (`tasks/`): Redis broker, RedBeat scheduler. Files: `ingest_tasks.py`, `cleanup_tasks.py`, `scheduled_tasks.py`, `triage_tasks.py` (Stage 1, weekly), `score_tasks.py` (Stage 2 driver; retries only on no-full-text / TypeSafe transient errors, honors TypeSafe `retry_after`), `digest_tasks.py` (weekly `build_digest_task`), `demand_tasks.py` (nightly `backfill_demand_task`: retries NULL-demand Semantic Scholar lookups, SPE-284), `signals.py`, `tracing.py`. Flower at port 5555.

**Key patterns:**
- Dependency injection via `Depends()` with `Annotated` type aliases in `dependencies.py`
- Custom exceptions in `exceptions.py` with HTTP status mapping
- Structured logging via structlog + `get_logger(__name__)` with request ID correlation
- Clerk JWT auth for users; API key auth (`X-Api-Key`) for ops endpoints. Tiers (`tiers.py`): `TierPolicy(daily_chats)` only -- free 10/day, pro unlimited; `GET /users/me` returns `daily_chat_limit` / `chats_used_today` plus the feed profile.
- Hybrid search: pgvector + full-text with Reciprocal Rank Fusion
- LLM calls via LiteLLM with model prefix routing (`DEFAULT_LLM_MODEL`, currently `openai/gpt-5-nano`)

### Frontend (`/frontend/src/`)

React 19 + TypeScript + Vite. Zustand stores (chat streaming state, sidebar, user) for UI state; TanStack Query v5 for server state (`src/api/*.ts`, one module per domain with key factories + hooks). SSE streaming via `@microsoft/fetch-event-source`. React Router v7 with protected routes: `/feed` is home (sign-in, OAuth and landing CTAs land there; `/chat/*` redirects to it), `/papers/:arxivId`, `/library`, `/settings`, and `/onboarding` outside the sidebar layout. Clerk auth. Tailwind CSS v4 (light-only warm stone theme, tokens in `src/index.css`). One markdown renderer (`components/chat/MarkdownRenderer.tsx` lazily loads `MarkdownBody`: GFM + remark-math/KaTeX + arXiv links + Prism, always on); the privacy page renders `src/content/privacy-policy.md` through the same component map. Feed UI: `src/pages/FeedPage.tsx` + `src/components/feed/*` (cards, verdict line, score badge, signal chips, Save / Dismiss / Implementing with optimistic cache updates in `src/api/paperState.ts`); `src/pages/PaperDetailPage.tsx` + `src/components/paper/*` (per-dimension breakdown; `src/api/scores.ts` polls the 202 response every 5 s for up to 3 min); `src/pages/OnboardingPage.tsx` + `src/components/onboarding/*` (`OnboardingGate` in `App.tsx` redirects `me.onboarded === false` to `/onboarding`; the same form is editable under Settings). Chat exists only as `src/components/paper/ScopedChatPanel.tsx` on paper detail: `useChat(sessionId, { arxivId, onSessionCreated })` sends `{query, arxiv_id, session_id}`, keeps a per-paper draft key, and shows one status line from `chatStore.currentStatus` while streaming (no thinking timeline, no HITL, no per-request LLM settings); the global `useChatStore` allows one mounted chat surface at a time, so the panel aborts on unmount; `?session=` selects a thread. Tiers on the client are `daily_chat_limit` / `chats_used_today` only. Tests live under `frontend/tests/**` (vitest + jsdom).

### Database

PostgreSQL 16 + pgvector. Migrations via Alembic (`backend/alembic/`). Tables: papers, chunks, conversations, conversation_turns, users, task_executions, usage_counters, plus the feed-pivot scoring tables paper_scores, score_evidence, user_paper_states, digests (migrations `019_add_scoring_tables`, `020_add_score_dimensions`, `021_add_conversation_paper_id`, `022_drop_chat_first_leftovers`; see `docs/design/scoring-pipeline.md`). Migration 022 dropped `agent_executions` and the HITL/ingest-quota columns; the test DB keeps `alembic_version` after `just test` drops the tables, so run `DROP TABLE alembic_version` before an `alembic upgrade head` there.

### Infrastructure

Docker profiles: `dev`, `prod`, `test`, `eval`. Redis, Langfuse (self-hosted), Flower. See `docker-compose.yml` for service details.

### Deployment (Coolify) & branch strategy

Production is a single Coolify docker-compose app deploying `docker-compose.coolify.yml`. **During the feed pivot, prod is frozen on the `production` branch and curtained behind a maintenance screen -- it does NOT track `main`.** Develop on `main` (Coolify does not auto-deploy it); Phase 1 work merges there freely with no prod impact.

- **Maintenance curtain** (env-flagged, default off): backend `MAINTENANCE_MODE=true` -> `maintenance_middleware` returns 503 for all routes except health; frontend `VITE_MAINTENANCE_MODE=true` (build-time -- wired as a compose build arg in `docker-compose.coolify.yml` + `frontend/Dockerfile`) -> renders `MaintenanceScreen`.
- **Relaunch**: merge `main -> production`, set both flags to `false` in the Coolify env, redeploy (a rebuild, so the frontend flag re-bakes).
- **LLM model env:** `DEFAULT_LLM_MODEL` and `STRUCTURED_OUTPUT_MODEL` (both `openai/gpt-5-nano`) are the only model settings; the allowlist, the NVIDIA NIM provider and `REDIS_CHECKPOINT_URL` were removed in SPE-298. Stale keys in the Coolify env (`ALLOWED_LLM_MODELS`, `NVIDIA_NIM_*`, `REDIS_CHECKPOINT_URL`, `MAX_RETRIEVAL_ATTEMPTS`) are ignored.
- **Semantic Scholar (SPE-284):** runs keyless by design. `SemanticScholarClient` spaces requests across all workers with a Redis slot (`SEMANTIC_SCHOLAR_MIN_INTERVAL_MS`, default 1500 ms) so concurrent scoring tasks cannot burst the shared ~1 req/s pool; a lookup that still 429s soft-fails to NULL (the composite renormalizes) and `backfill_demand_task` fills it in nightly. No API key is needed at weekly volumes.
- **TypeSafe env (SPE-286):** Stage 2 scoring needs `TYPESAFE_API_KEY` (required in `docker-compose.coolify.yml` for both `backend` and `worker`); `TYPESAFE_MODEL` defaults to `jev-1.13.0`. The Jev model is not a LiteLLM model. Chat and Stage 1 triage do not use it.
- External API base is `/api` (frontend nginx rewrites `/api/` -> backend `/api/v1/`); the public health path is `/api/health`.

## Code Style

- Python: 100 char lines, type hints on all functions, async/await for I/O, `get_logger(__name__)`, exceptions from `src/exceptions.py`
- TypeScript: strict mode, functional components, Zustand for state; Prettier (no semicolons, single quotes, 100 cols, Tailwind class order) and type-checked ESLint (`recommendedTypeChecked`, `import-x` order/no-cycle, vitest + testing-library rules in `tests/`); `knip` fails the lint on unused files, exports and deps
- No emojis in code or comments
