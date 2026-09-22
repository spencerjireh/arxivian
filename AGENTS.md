# AGENTS.md

Arxivian: a weekly feed of arXiv papers scored for implementability, with a chat scoped to
each paper. FastAPI + React + PostgreSQL/pgvector + LangGraph + Celery. This file is the
as-built map for people and coding agents; `CLAUDE.md` is a symlink to it. Design intent
lives in `docs/`; process (branches, PRs, releases) in `CONTRIBUTING.md`. Update this file
in the same PR as the code it describes. Prose is dry and factual; no emojis anywhere.

## Commands

All development runs in Docker via `just`; `just --list` groups every recipe.

```bash
just setup                        # copy backend/.env, backend/.env.test, frontend/.env from .example
just dev                          # build + start with hot reload (just down / just clean)
just test tests/unit tests/api    # what CI gates (bare `just test` also collects tests/evals)
just test tests/integration       # repositories + migrations against the test DB (port 5433)
just test -k "pattern"            # any pytest args pass through
just check                        # ruff + ty + eslint/knip/prettier/tsc, both trees
just fix / just format-frontend   # auto-fix
just ci                           # every CI step locally except the image builds (needs just up-d)
just deadcode                     # vulture, advisory
just eval                         # LLM-backed evals (real OPENAI_API_KEY)
just inteval-seed && just inteval -k scoring   # golden-set scoring eval (real TypeSafe key)
just migrate / just shell-backend / just db-shell / just logs app
```

Git hooks: `uvx pre-commit install` (ruff from `backend/uv.lock`, lint-staged for the
frontend; needs uv and Node 22 on the host, see `CONTRIBUTING.md`).

## Repository map

```
AGENTS.md, CLAUDE.md -> AGENTS.md, README.md (public), CONTRIBUTING.md, SECURITY.md
justfile                       every dev command; docker-compose.yml (dev/test/eval/inteval)
docker-compose.coolify.yml     production stack; validated by the CI docker job
.github/workflows/ci.yml       seven required checks; release.yml tags production pushes
backend/
  src/main.py                  FastAPI app, lifespan, middleware, nine routers under /api/v1
  src/factories.py             the only construction module (clients, services, agent, auth)
  src/dependencies.py          FastAPI Depends wiring only (Annotated aliases)
  src/config.py                Settings (pydantic-settings; CLERK_DOMAIN is the one required field)
  src/exceptions.py            one exception per HTTP status with a stable error_code
  src/observability.py         Logfire/OTel; the only module that imports logfire
  src/tiers.py                 TierPolicy(daily_chats): free 10/day, pro unlimited; system user
  src/celery_app.py            Celery + RedBeat schedule
  src/routers/                 HTTP layer, one file per resource
  src/schemas/                 request/response shapes, one module per router (+ errors.py)
  src/services/                agent_service/, scoring_service/, feed_service/, ingest, search, auth, chunking
  src/repositories/            one module per table (async SQLAlchemy)
  src/models/                  ORM models (models/__init__ is star-imported by alembic/env.py)
  src/clients/                 LiteLLM (chat + embeddings), arXiv, Semantic Scholar, TypeSafe
  src/tasks/                   Celery tasks; runtime.py owns the worker loop; signals.py the hooks
  src/middleware/              error handler, request logging, maintenance curtain
  src/utils/                   logger, pdf_parser, section_splitter
  alembic/versions/            NNN_slug.py, named by revision id
  tests/{unit,api,integration,evals}/   mirror the markers; evals/integration is the inteval suite
frontend/
  src/App.tsx                  the only router (AuthSession > Layout > lazy pages; ProtectedRoute on account pages)
  src/main.tsx                 Clerk + QueryClient + ErrorBoundary; maintenance switch
  src/api/                     TanStack Query, one module per backend domain, key factories + hooks
  src/api/client.ts            fetch wrapper; API base is /api (nginx rewrites to /api/v1)
  src/types/api.ts             hand-mirrored backend schemas; update with every schema change
  src/components/<feature>/    feed, paper, chat, onboarding, settings, landing, layout (TopNav), auth, ui
  src/pages/                   one file per route
  src/stores/                  Zustand (chat streaming, user); src/hooks/; src/lib/
  src/content/privacy-policy.md   rendered at /privacy
  tests/unit/**                vitest + jsdom, mirrors src/
docs/product/feed-prd.md       product-of-record; docs/design/ scoring pipeline + rubric; docs/ops/ runbooks
```

Every frontend module starts with a one-line `//` header naming its responsibility and its
backend twin where one exists; every backend module has a docstring. Grep either tree by
route or table name to find the other side.

## Backend

Layering: `routers -> services -> repositories -> models`. `factories.py` builds clients,
services, the agent and `AuthService` (`lru_cache` singletons; per-request objects take a
session). Custom exceptions map to HTTP in `middleware/error_handler.py`. Logging is
structlog via `get_logger(__name__)` with request-id correlation and the OTel trace id.
Auth: Clerk JWT for users, `X-Api-Key` for ops endpoints. LLM calls go through LiteLLM;
`DEFAULT_LLM_MODEL` and `STRUCTURED_OUTPUT_MODEL` (both `openai/gpt-5-nano`) are the only
model settings.

**Paper-scoped chat agent** (`services/agent_service/`): a LangGraph graph compiled once,
no checkpointer: classify_and_route -> executor -> evaluate_batch -> generate, plus
out_of_scope; evaluate can loop back to classify up to `MAX_ITERATIONS`. State and
structured-output models in `state.py`; three tools in `tools/` (retrieve_chunks over
`SearchService.retrieve_within_paper`, explore_citations, semantic_scholar); prompts in
`prompts.py`; `title.py` names a thread. `POST /stream` takes `{query, arxiv_id,
session_id?}` and nothing else (`extra="forbid"`), streams SSE events (`schemas/stream.py`),
and persists the scope on `conversations.paper_id`, which wins on follow-ups
(`routers/stream.py::resolve_scoped_paper`; 409 `PAPER_NOT_INGESTED` / `SCOPE_MISMATCH`).
`GET /conversations?arxiv_id=` lists a paper's threads; another user's session id is a
403. There is no HITL ingest, no corpus search, no resume, no server-side cancel.

**Scoring pipeline** (`services/scoring_service/`, rubric v2): Stage 1 triage
(`triage.py`, batched abstracts on the default LLM, weekly `triage_tasks.py`) feeds Stage
2, a fixed fan-out/fan-in LangGraph DAG (fetch_and_extract -> four dimension nodes ->
compose_and_persist) driven by `score_tasks.py`. Judgments come from TypeSafe Jev
(`clients/typesafe_client.py`; typed answers with calibrated probabilities): method
clarity = 4 Nouls combined by a Poisson-binomial, resource feasibility = 1 compute-tier
Score + 2 Nouls, data availability = 1 Choice regrouped into a PASS/FAIL gate; demand =
Semantic Scholar citations (no LLM). Questions in `questions.py`, combine rules in
`judgments.py`, stored shape in `state.py`: per-dimension level distribution + atomic
judgments in `paper_scores.dimensions` (JSONB), the `*_score` integers are derived, product
attributes in `paper_scores.attributes`. See `docs/design/scoring-pipeline.md` and
`docs/design/scoring-rubric.md` (linked from the code; the rubric source of truth).

**Feed read path** (`services/feed_service/`): `digest.py` (week key, composite weights,
`compute_composite`) is written by the weekly `build_digest_task` and read by
`FeedService`; `derive.py` turns a `PaperScore` row into card fields in pure code (read-time
composite with NULL renormalization, compute-profile match, template verdict from the Jev
judgments, signal chips, low-confidence marker); `service.py` batch-loads the live rows for
a digest week. Routers: `feed` (`GET /feed`), `paper_states` (`PUT`/`DELETE
/papers/{arxiv_id}/state`, `GET /users/me/library` grouped saved / implementing / shipped),
`papers` (`GET /papers/{arxiv_id}/score`: full breakdown with `score_evidence` spans; an
unscored paper enqueues `score_paper_task` behind a Redis `SET NX` lock
`score:ondemand:{arxiv_id}` and answers 202 until a poll finds a score; each new enqueue
counts against two Redis day counters, `ONDEMAND_SCORE_DAILY_BUDGET` across all users and
`ONDEMAND_SCORE_DAILY_PER_USER`, past which it is a 429 `SCORING_LIMIT_EXCEEDED`). The
onboarding
profile lives in `users.preferences["feed_profile"]` (`schemas/users.py::FeedProfile`,
`PATCH /users/me/preferences`, read back on `GET /users/me` with `onboarded`); per-user
`weights` are reserved, not settable.

**Celery** (`tasks/`): Redis broker, RedBeat scheduler, Flower on 5555. `ingest_tasks`,
`cleanup_tasks`, `scheduled_tasks` (nightly ingest), `triage_tasks` (weekly Stage 1),
`score_tasks` (Stage 2; retries only on no-full-text / TypeSafe transient errors, honors
`retry_after`), `digest_tasks` (weekly), `demand_tasks` (nightly backfill of NULL demand),
`embedding_tasks` (`reembed_chunks_task`, run by hand after an embedding-model change;
keyset cursor, re-enqueues itself under the task time limit).
`runtime.py` owns the per-process event loop and `run_async`; `signals.py` starts it,
configures tracing and tracks `task_executions` status. `tasks/__init__.py` imports every
task module so `autodiscover_tasks` registers them; keep it that way.

**Database**: PostgreSQL 16 + pgvector. Tables: papers, chunks, conversations,
conversation_turns, users, task_executions, usage_counters, paper_scores, score_evidence,
user_paper_states, digests. Migrations in `backend/alembic/versions/`, files named by
revision id; add one with `uv run alembic revision --rev-id 023_slug -m "..."`. Hybrid
search is pgvector HNSW + tsvector fused by RRF (`repositories/search_repository.py`).

**Tracing**: Pydantic Logfire over OpenTelemetry (`observability.py`). `configure_tracing()`
runs at API import and per worker process; it instruments LiteLLM, httpx, LangGraph
(OpenInference), FastAPI, SQLAlchemy and Celery, and `utils/logger.py` ships structlog lines
to the active span. Empty `LOGFIRE_TOKEN` (dev, CI) exports nothing; the SDK reads the
token from `backend/.env` itself. Prompts and paper text are sent by design.
`AgentService.ask_stream` wraps a turn in a `chat.turn` span.

## Frontend

React 19 + TypeScript strict + Vite; Tailwind v4 (light-only warm stone theme, tokens in
`src/index.css`); Clerk auth; React Router v7. The feed is public and lives at `/`
(`/feed` and `/chat/*` redirect there, keeping the query string); `/papers/:arxivId`,
`/about` (the marketing page), `/pricing` and `/privacy` are public too; `/library` and
`/settings` sit behind `ProtectedRoute`; `/onboarding`, `/sign-in`, `/sign-up` and
`/sso-callback` render outside the shell. `components/auth/AuthSession.tsx` is the root
layout route: it registers Clerk's token getter with `api/client.ts` (a null getter when
signed out), waits for Clerk to load, fetches `/users/me` only for a signed-in visitor and
handles the forced sign-out that `api/client.ts` raises on a 401 to a request that carried
a token. `components/layout/Layout.tsx` is a document page (window scroll): `TopNav`
(Feed, About, Pricing; Library, Settings and `UserMenu` when signed in; `SignInLink`
otherwise), the page, `Footer`. There is no sidebar and no onboarding gate. Sign-in returns
to `location.state.from` (`lib/nav.ts::returnPathFrom`, same-origin paths only) through
`OAuthButtons`' `redirectUrlComplete`; every sign-in prompt is `components/auth/SignInLink.tsx`.

Server state is TanStack Query v5 (`src/api/*.ts`, key factories + hooks, optimistic
lifecycle updates in `api/paperStates.ts`); UI state is Zustand (`src/stores/`). Chat exists
only as `components/paper/ScopedChatPanel.tsx`: `useChat(sessionId, { arxivId })` posts
`{query, arxiv_id, session_id}` over `@microsoft/fetch-event-source`, keeps a per-paper
draft, and shows one status line; `useChatStore` allows one mounted chat surface, so the
panel aborts on unmount; `?session=` selects a thread. One markdown renderer
(`components/chat/MarkdownRenderer.tsx` lazily loads `MarkdownBody`: GFM, remark-math/KaTeX,
arXiv links, Prism); the privacy page uses the same component map. `api/scores.ts` polls
the 202 every 5 s for up to 3 min. Tiers on the client are `daily_chat_limit` /
`chats_used_today` only.

## Testing and CI

Markers `unit`, `api`, `integration`, `eval`, `inteval`; dirs mirror them and each dir's
conftest applies the marker. Pytest: `asyncio_mode = "auto"` (session loop),
`filterwarnings = error`, `--strict-markers`. Coverage ratchets: backend `fail_under` in
`pyproject.toml` (unit + api, with the `omit` list), frontend thresholds in
`vitest.config.ts`; raise them when the number goes up, never lower. Integration tests read
`TEST_DATABASE_URL` directly (set in `.env.test`; `TEST_DB_PORT` overrides the host port).

CI (`.github/workflows/ci.yml`) runs seven required checks on every PR: Backend lint (uv
lock check, ruff, ty), Backend unit + api (coverage gate), Backend integration (pgvector
service, migration round trip), Frontend lint (eslint + knip, prettier, tsc), Frontend
tests (vitest thresholds), Docker images + coolify compose (the only check that exercises
the relaunch path), PR title (conventional commit; squash-merge uses it). Actions are
SHA-pinned; Dependabot bumps them, uv and npm weekly. `just ci` runs the same steps locally.

## Deployment

Production is one Coolify docker-compose app deploying `docker-compose.coolify.yml` from
the `production` branch; Coolify does not track `main`. Promote with a `main -> production`
PR merged with a merge commit; every push to `production` is tagged `vYYYY.MM.DD[.n]` with
generated release notes (`release.yml`). Moving the stack between servers:
`docs/ops/coolify-migration.md`.

- Maintenance curtain: backend `MAINTENANCE_MODE=true` -> 503 for all routes except health;
  frontend `VITE_MAINTENANCE_MODE=true` is a build arg (`frontend/Dockerfile`), so flipping
  it means a rebuild. The two flags are the rollback lever: set both in the Coolify env
  (prod and preview rows) and redeploy, no code change. Relaunched 2026-09-21 curtained,
  opened 2026-09-22.
- Run a task by hand: `docker exec <celery-worker> uv run celery -A src.celery_app call
  src.tasks.triage_tasks.triage_new_papers_task` (same for `digest_tasks.build_digest_task`).
- Compose env wiring: only variables listed under a service's `environment:` reach that
  container. Settings are validated at import, so `celery-beat` carries `CLERK_DOMAIN` plus
  the schedule crons; feed knobs (`TRIAGE_*`, `ONDEMAND_SCORE_LOCK_SECONDS`) are on `app`
  and `celery-worker`, the `ONDEMAND_SCORE_DAILY_*` budgets on `app` only.
  `TYPESAFE_API_KEY` is required for `backend` and `worker`.
- Semantic Scholar runs keyless: a Redis slot (`SEMANTIC_SCHOLAR_MIN_INTERVAL_MS`) spaces
  requests across workers; a 429 soft-fails to NULL demand and the nightly backfill retries.
- Stale Coolify keys (`ALLOWED_LLM_MODELS`, `NVIDIA_NIM_*`, `REDIS_CHECKPOINT_URL`,
  `MAX_RETRIEVAL_ATTEMPTS`) are ignored.
- External API base is `/api` (frontend nginx rewrites to `/api/v1`); public health path
  `/api/health`.

## Conventions

- Python: 100-char lines, type hints on every function, async for I/O, `get_logger(__name__)`,
  exceptions from `src/exceptions.py`, ruff rule set in `pyproject.toml`, ty on `src/`.
- TypeScript: strict, functional components, Prettier (no semicolons, single quotes, 100
  cols, Tailwind class order), type-checked ESLint with `import-x` order/no-cycle, knip fails
  on unused files/exports/deps. Header comment on every module.
- Docs: `AGENTS.md` is as-built and changes with the code; design docs carry a Status line
  and record intent; README is the public overview. No emojis in code, comments or docs.
- PR titles are conventional commits with the Linear id last (`CONTRIBUTING.md`).

## Gotchas

- The test DB keeps `alembic_version` after `just test` drops the tables: `DROP TABLE
  alembic_version` before an `alembic upgrade head` there.
- Host-port overrides (`BACKEND_PORT`, `FRONTEND_PORT`, `DB_PORT`, `REDIS_PORT`,
  `FLOWER_PORT`, `TEST_DB_PORT`) are compose interpolation from the shell, not `backend/.env`.
- A real `LOGFIRE_TOKEN` in `backend/.env` turns on live instrumentation for local pytest
  too; run `LOGFIRE_TOKEN="" uv run pytest ...` on the host.
- `VITE_*` values are baked at build time in production.
- `POST /stream` rejects unknown fields; the chat store allows one mounted panel at a time.
- Scoring needs `TYPESAFE_API_KEY`, but the client is built only inside the task, so the API
  starts without it. An on-demand score joins the feed only at the next digest build.
- `tasks/__init__.py`, `models/__init__.py` and `routers/__init__.py` are load-bearing
  indexes; the other package inits are docstrings only.
- If this file passes ~200 lines, move the Backend and Frontend sections into
  `backend/AGENTS.md` and `frontend/AGENTS.md` and keep the root as map + links.

## Docs index

- `docs/product/feed-prd.md`: product-of-record for the feed. `docs/product/user-stories.md`: pivot epics.
- `docs/design/scoring-pipeline.md`: two-stage pipeline and scoring graph. `docs/design/scoring-rubric.md`: rubric v2, linked from the code.
- `docs/ops/coolify-migration.md`: moving the stack between Coolify servers.
- `frontend/src/content/privacy-policy.md`: the privacy policy rendered at `/privacy`.
- `README.md`, `CONTRIBUTING.md`, `SECURITY.md`.
