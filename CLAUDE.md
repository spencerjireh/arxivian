# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arxivian -- full-stack agentic RAG system for analyzing arXiv papers. FastAPI + React + PostgreSQL/pgvector + LangGraph + Celery.

## Development Commands

All development runs in Docker via `just`. Run `just --list` for full list.

```bash
just dev                # Build and start with hot reload
just down               # Stop services
just logs               # View all logs
just test               # All tests (spins up test containers)
just test tests/integration/test_file.py::test_func   # Single test
just test -k "pattern"  # Pattern match
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

Test markers: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`, `@pytest.mark.e2e`. Test dirs: `tests/unit/`, `tests/api/`, `tests/integration/`, `tests/e2e/`. Integration tests use a dedicated test DB (port 5433), config in `.env.test`.

## Architecture

### Backend (`/backend/src/`)

Layered: `routers/` -> `services/` -> `repositories/` -> `models/` (async SQLAlchemy). Also: `schemas/` (Pydantic), `clients/` (OpenAI, arXiv, Jina, Langfuse), `middleware/`, `factories/`.

**Agent service** (`services/agent_service/`): LangGraph workflow with nodes: guardrail -> router -> executor -> grading -> generation. Tools: retrieve, arxiv_search, ingest, summarize_paper, list_papers, explore_citations.

**Celery tasks** (`tasks/`): Redis broker, worker + beat containers. Files: `ingest_tasks.py`, `cleanup_tasks.py`, `scheduled_tasks.py` (includes report generation), `signals.py`, `tracing.py` (Langfuse singleton for workers). Flower at port 5555.

**Key patterns:**
- Dependency injection via `Depends()` with type aliases in `dependencies.py`
- Custom exceptions in `exceptions.py` with HTTP status mapping
- Structured logging via `utils/logger.py` with request ID correlation
- Clerk JWT auth for users; API key auth for ops endpoints
- Hybrid search: pgvector + full-text with Reciprocal Rank Fusion
- LLM calls via LiteLLM with model prefix routing (e.g. `openai/gpt-4o-mini`)

### Frontend (`/frontend/src/`)

React 19 + TypeScript + Vite. Zustand stores (chat, settings, sidebar). SSE streaming via `@microsoft/fetch-event-source`. React Router v7 with protected routes. Clerk auth. Tailwind CSS v4.

### Database

PostgreSQL 16 + pgvector. Tables: papers, chunks, conversations, conversation_turns, users, agent_executions, task_executions, usage_counters, reports. Migrations via Alembic (`backend/alembic/`).

### Infrastructure

Redis (6379), Langfuse (3001), Flower (5555), Test DB (5433). Docker profiles: `dev`, `prod`, `test`.

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`): ruff, ty, unit/API tests (backend); eslint, tsc, vitest (frontend). Pre-commit hooks: trailing whitespace, detect-secrets, ruff, eslint.

## Code Style

- Python: 100 char lines, type hints on all functions, async/await for I/O, `get_logger(__name__)`, exceptions from `src/exceptions.py`
- TypeScript: strict mode, functional components, Zustand for state
- No emojis in code or comments
