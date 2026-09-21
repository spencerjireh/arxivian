<div align="center">

<img src="assets/logo-full.png" alt="Arxivian" width="320" />

**A weekly feed of arXiv papers you could actually implement.**

Arxivian scores new ML papers on method clarity, resource feasibility, data availability and demand, ranks them for your compute budget and interests, and lets you chat with each paper's full text.

[![CI](https://github.com/spencerjireh/arxivian/actions/workflows/ci.yml/badge.svg)](https://github.com/spencerjireh/arxivian/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/postgresql-16-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/license-AGPL--3.0-blue)

</div>

---

## How It Works

1. **Triage (weekly, cheap).** New papers in your categories are fetched from arXiv and filtered by a small LLM pass.
2. **Score (per paper).** The full text is ingested and judged by TypeSafe Jev on four dimensions: method clarity, resource feasibility (compute tier), data availability (a PASS/FAIL gate) and demand (Semantic Scholar citations). Every judgment carries quoted evidence and a calibrated confidence.
3. **Digest (weekly).** Scores are snapshotted into a ranked digest per category set.
4. **Feed (read time).** Cards show a composite score, a one-line verdict, signal chips (pseudocode, public datasets, single GPU, code released) and a fit marker for your compute profile. Save, dismiss or mark papers as implementing; open one for the per-dimension breakdown and a chat scoped to that paper.

`docs/product/feed-prd.md` is the product-of-record; `docs/design/scoring-pipeline.md` and `docs/design/scoring-rubric.md` describe the pipeline and the rubric; `AGENTS.md` maps the code for people and coding agents (`CLAUDE.md` is a symlink to it); `CONTRIBUTING.md` covers branches, checks and releases; `docs/ops/coolify-migration.md` is the server-move runbook.

## Architecture

<div align="center">
<img src="public/architecture.png" alt="System Architecture" width="700" />
</div>

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Zustand |
| **Backend** | FastAPI, Python 3.11, async SQLAlchemy 2.0, Pydantic v2 |
| **Scoring** | TypeSafe Jev (typed judgments with calibrated probabilities), LangGraph fan-out DAG |
| **Chat** | LangGraph agent scoped to one paper, LiteLLM, SSE streaming |
| **Retrieval** | pgvector HNSW (vector), PostgreSQL GIN/tsvector (full-text), Reciprocal Rank Fusion |
| **Embeddings** | Jina Embeddings v3 (1024d) |
| **Auth** | Clerk (JWT + Google OAuth), tiered rate limiting |
| **Async** | Celery 5 + Redis (broker), RedBeat (scheduler), Flower (monitoring) |
| **Observability** | Pydantic Logfire (OpenTelemetry; FastAPI, SQL, LangGraph, LiteLLM, Celery), structlog with request ID correlation |
| **Infra** | Docker Compose (dev/test/prod/eval profiles), Alembic migrations, Coolify |
| **CI** | GitHub Actions -- lint, unit/api + integration (pgvector service), coverage gates, image builds, PR-title check |

## Quick Start

**Prerequisites:** Docker, Docker Compose, [just](https://github.com/casey/just). For the git hooks also uv and Node 22 (see `CONTRIBUTING.md`).

```bash
git clone https://github.com/spencerjireh/arxivian.git
cd arxivian

just setup              # Copy backend/.env, backend/.env.test, frontend/.env from their .example files
# Fill in the keys listed below in backend/.env and frontend/.env
just dev                # Build and start everything with hot reload
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Flower | http://localhost:5555 |

### Required API Keys

| Key | File | Purpose |
|-----|------|---------|
| `OPENAI_API_KEY` | `backend/.env` | Triage and chat LLM calls via LiteLLM |
| `TYPESAFE_API_KEY` | `backend/.env` | Stage 2 scoring (Jev). Chat and triage do not use it; the API starts without it |
| `JINA_API_KEY` | `backend/.env` | Document embeddings (Jina v3) |
| `CLERK_DOMAIN` | `backend/.env` | Clerk instance domain; JWTs are verified against its JWKS. The only setting with no default |
| `VITE_CLERK_PUBLISHABLE_KEY` | `frontend/.env` | Clerk auth UI |

Semantic Scholar runs keyless (requests are paced through a Redis slot). Host-port overrides (`BACKEND_PORT`, `FRONTEND_PORT`, `DB_PORT`, `REDIS_PORT`, `FLOWER_PORT`) are compose interpolation variables: set them in the shell, not in `backend/.env`.

## Development

```bash
just dev                          # Start all services with hot reload
just down                         # Stop services
just test tests/unit tests/api    # Backend unit + api (what CI gates)
just test tests/integration       # Repositories and migrations against the test DB
just test -k "pattern"            # Any pytest args pass through
just check                        # Lint + typecheck, both trees
just ci                           # Every CI step locally (needs just up-d)
just fix                          # Auto-fix backend lint + format
just test-frontend                # Vitest
just eval                         # LLM-backed evals (requires API keys)
just inteval-seed && just inteval -k scoring   # Golden-set scoring eval against the real judge
just migrate                      # Run Alembic migrations
just --list                       # All recipes, grouped
```

## Key Design Decisions

**Typed judgments instead of free-text grading.** Scoring asks a judge model closed questions (yes/no, a choice, a level) and stores the full probability distribution plus the quoted evidence. The stored integers are denormalizations; the composite is recomputed at read time so weights can change without re-scoring.

**Read-time ranking.** The digest caches membership and a provisional order; personalization (compute-profile fit, keyword tie-breaks, NULL-safe weight renormalization) is computed per request from the live rows.

**Hybrid retrieval with RRF.** pgvector HNSW plus PostgreSQL GIN/tsvector fused by Reciprocal Rank Fusion, with no external search engine. Paper-scoped chat retrieves inside one paper only.

**Communal knowledge base.** Ingested papers are shared across users; scoring a paper once serves everyone.

**OpenTelemetry for tracing.** Instrumentation is vendor-neutral (FastAPI, SQLAlchemy, httpx, Celery, LiteLLM, LangGraph via OpenInference); Logfire is the exporter today and swappable by env.

## Testing

| Suite | Marker | What it covers |
|-------|--------|---------------|
| Unit | `unit` | Schemas, services, nodes, tasks, clients (mocked I/O) |
| API | `api` | Routers with mocked dependencies |
| Integration | `integration` | Repositories and migrations against a real pgvector database |
| Eval | `eval`, `inteval` | Golden-set agreement for chat and scoring (real API keys; run by hand, not in CI) |

```bash
just test tests/unit tests/api     # unit + api
just test tests/integration        # integration (test DB on port 5433)
just eval                          # LLM evals (real OPENAI_API_KEY)
just inteval-seed && just inteval  # golden-set scoring eval (real TypeSafe key + seeded DB)
```

## License

[AGPL-3.0](LICENSE)
