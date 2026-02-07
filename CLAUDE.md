# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jireh's Agent is a full-stack agentic RAG (Retrieval-Augmented Generation) system for analyzing arXiv research papers with multi-turn conversation support and observability.

## Development Commands

### Docker Development (Default)
```bash
just setup    # Initialize .env from .env.example
just dev      # Build and start with hot reload
just up       # Start services (after building)
just down     # Stop services
just clean    # Clean up everything
just logs     # View all logs
just rebuild  # Build with no cache (clean build)
just restart  # Restart all services
just ps       # Check status of all services
just reset    # Full reset: clean everything and rebuild
just exec-backend "cmd"    # Execute command in backend container
just exec-frontend "cmd"   # Execute command in frontend container
just logs-service <name>   # View logs from specific service
just health                # Check backend health endpoint
```

### Backend (Python)
```bash
uv run ruff check src/        # Lint
uv run ruff format src/       # Format
uv run ty check src/          # Type check
uv run alembic upgrade head   # Run migrations
```

### Database
```bash
just db-shell    # PostgreSQL shell
just migrate     # Run Alembic migrations
```

### Testing
```bash
just test                                              # All integration/E2E tests
just test tests/integration/test_file.py::test_func   # Single test
just test -k "pattern"                                 # Pattern match
just test-clean                                        # Cleanup test containers
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`, `@pytest.mark.e2e`

Test directory structure: `tests/unit/`, `tests/api/`, `tests/integration/`, `tests/e2e/`. Integration tests use a dedicated test database (port 5433) with automatic Alembic migrations. Test config in `.env.test`.

### Frontend (TypeScript/React)
Run inside frontend container (`just shell-frontend`):
```bash
npm run lint    # ESLint
npm run build   # Production build
npm run dev     # Dev server
```

## Architecture

### Backend (`/backend/src/`)

**Layered Architecture:**
- `routers/` - FastAPI route handlers (search, ingest, stream, papers, conversations, admin, feedback, health)
- `services/` - Business logic layer
- `repositories/` - Data access layer with async SQLAlchemy
- `models/` - SQLAlchemy ORM models (Paper, Chunk, Conversation, ConversationTurn, User)
- `schemas/` - Pydantic request/response models
- `clients/` - External service integrations (OpenAI, arXiv, Jina embeddings, Langfuse)
- `middleware/` - Request logging, transaction management, error handling
- `factories/` - Dependency injection factories

**Agent Service (`services/agent_service/`):**
- LangGraph-based agentic workflow with named nodes:
  - `guardrail` - Input validation and safety checks
  - `router` - Dynamic tool selection based on query analysis
  - `executor` - Tool execution
  - `grading` - Retrieval quality assessment
  - `generation` - Final response generation
- `tools/` - Agent tools (retrieve, arxiv_search, ingest, summarize_paper, etc.)
- `context.py` - Thread-safe state management
- `prompts.py` - System prompts

**Celery Background Tasks (`tasks/`):**
- Celery with Redis as message broker; worker and beat services run as separate containers
- `ingest_tasks.py` - Paper ingestion from arXiv
- `cleanup_tasks.py` - Data retention cleanup
- `report_tasks.py` - Scheduled report generation
- `scheduled_tasks.py` - Cron-scheduled job definitions
- `signals.py` - Worker lifecycle and task tracking signals
- Flower monitoring dashboard available at port 5555

**Key Patterns:**
- Dependency injection via FastAPI `Depends()` with type aliases in `dependencies.py`
- Custom exceptions in `exceptions.py` with HTTP status mapping
- Structured logging via `utils/logger.py` with request ID correlation
- Clerk JWT authentication with user sync to local database
- Hybrid search using pgvector + full-text with Reciprocal Rank Fusion

### Frontend (`/frontend/src/`)

- `pages/` - Route pages (ChatPage, SignInPage, SignUpPage)
- `components/` - React components organized by feature (auth, chat, layout, sidebar, ui)
- `api/` - API client with auth token injection and SSE streaming
- `stores/` - Zustand state management (chatStore, settingsStore, sidebarStore)
- `hooks/` - Custom React hooks (useChat, useAutoScroll, useDebounce)
- `lib/` - Utilities for markdown rendering and animations

**Key Patterns:**
- React Router v7 with `createBrowserRouter` and protected routes
- SSE streaming via `@microsoft/fetch-event-source` for real-time responses
- Clerk authentication with custom sign-in/sign-up forms

### Database

PostgreSQL 16 with pgvector extension:
- `papers` - arXiv metadata and processing status
- `chunks` - Document chunks with vector embeddings
- `conversations` / `conversation_turns` - Multi-turn memory
- `users` - Synced from Clerk
- `agent_executions` - Execution history for observability

Migrations via Alembic in `backend/alembic/`.

### Infrastructure Services

- **Redis** (port 6379) - Celery message broker
- **Langfuse** (port 3001) - LLM observability platform (with its own PostgreSQL instance)
- **Flower** (port 5555) - Celery task monitoring
- **Test DB** (port 5433) - Separate PostgreSQL for integration tests

Docker profiles: `dev`, `prod`, `test`. Backend uses multi-stage Dockerfile with `BUILD_TARGET=development` for hot reload.

## Code Style

### Python
- Line length: 100 characters
- Type hints required on all functions
- Async/await for I/O operations
- Use `get_logger(__name__)` from `src/utils/logger.py`
- Use exceptions from `src/exceptions.py`

### TypeScript/React
- Strict TypeScript mode
- Functional components with hooks
- Tailwind CSS v4 for styling
- Zustand for state management

### General
- No emojis in code or comments
- API docs available at `/docs`
