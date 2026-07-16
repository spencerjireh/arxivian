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
just lint               # Ruff linter
just format             # Ruff formatter
just fix                # Auto-fix lint and format issues
just check              # Lint + typecheck
just eval               # Run LLM-backed evals (requires API keys)
just migrate            # Run Alembic migrations
just shell-backend      # Shell in backend container
just clean              # Stop, remove volumes + local images
just lint-frontend      # ESLint via docker
just test-frontend      # Vitest via docker
```

Backend tools (run inside container or with `just exec-backend`):
```bash
uv run ruff check src/        # Lint
uv run ruff format src/       # Format
uv run ty check src/          # Type check
uv run alembic upgrade head   # Run migrations
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.eval`. Test dirs mirror markers. Pytest runs with `asyncio_mode = "auto"` (session-scoped loop). Coverage threshold: `fail_under = 80`. Integration tests use a dedicated test DB (port 5433), config in `.env.test`.

## Architecture

### Backend (`/backend/src/`)

Layered: `routers/` -> `services/` -> `repositories/` -> `models/` (async SQLAlchemy). Also: `schemas/` (Pydantic), `clients/` (LiteLLM/LLM, arXiv, Jina, Langfuse; planned: GitHub, Semantic Scholar), `middleware/`, `factories/`.

**Agent service** (`services/agent_service/`): the chat Q&A LangGraph workflow with nodes: classify_and_route -> executor -> evaluate_batch -> generate, plus out_of_scope and confirm_ingest (HITL). Tools (in `tools/`): retrieve_chunks, arxiv_search, ingest_papers, propose_ingest, list_papers, explore_citations. SSE streaming with custom event types (STATUS, CONTENT, SOURCES, CITATIONS, INGEST_COMPLETE, DONE).

**Scoring service** (`services/scoring_service/`, planned -- feed pivot): a second LangGraph workflow, a fixed fan-out/fan-in DAG (fetch_and_extract -> 5 parallel dimension nodes -> compose_and_persist) that scores papers for implementability. No streaming, no checkpointer. See `docs/design/scoring-pipeline.md`.

**Celery tasks** (`tasks/`): Redis broker, RedBeat scheduler. Files: `ingest_tasks.py`, `cleanup_tasks.py`, `scheduled_tasks.py`, `signals.py`, `tracing.py`; planned (pivot): `triage_tasks.py` (Stage 1), `score_tasks.py` (Stage 2 driver), `build_digest_task`. Flower at port 5555.

**Key patterns:**
- Dependency injection via `Depends()` with `Annotated` type aliases in `dependencies.py`
- Custom exceptions in `exceptions.py` with HTTP status mapping
- Structured logging via structlog + `get_logger(__name__)` with request ID correlation
- Clerk JWT auth for users; API key auth (`X-Api-Key`) for ops endpoints
- Hybrid search: pgvector + full-text with Reciprocal Rank Fusion
- LLM calls via LiteLLM with model prefix routing (e.g. `openai/gpt-4o-mini`)

### Frontend (`/frontend/src/`)

React 19 + TypeScript + Vite. Zustand stores (chat, settings, sidebar, user). SSE streaming via `@microsoft/fetch-event-source`. React Router v7 with protected routes. Clerk auth. Tailwind CSS v4. Markdown rendering with KaTeX math support.

### Database

PostgreSQL 16 + pgvector. Migrations via Alembic (`backend/alembic/`). Tables: papers, chunks, conversations, conversation_turns, users, agent_executions, task_executions, usage_counters. Planned (feed pivot): paper_scores, score_evidence, user_paper_states, digests (see `docs/design/scoring-pipeline.md`).

### Infrastructure

Docker profiles: `dev`, `prod`, `test`, `eval`. Redis, Langfuse (self-hosted), Flower. See `docker-compose.yml` for service details.

## Code Style

- Python: 100 char lines, type hints on all functions, async/await for I/O, `get_logger(__name__)`, exceptions from `src/exceptions.py`
- TypeScript: strict mode, functional components, Zustand for state
- No emojis in code or comments
