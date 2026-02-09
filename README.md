# Arxivian

Agentic RAG system for working with arXiv papers. Chat with an AI agent that can search, ingest, summarize, and explore citations across a shared knowledge base of research papers.

## Stack

- **Backend**: FastAPI, Python 3.11, async SQLAlchemy
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4
- **Database**: PostgreSQL 16 + pgvector
- **AI/ML**: LangGraph agent, LiteLLM (model routing), Jina Embeddings v3
- **Infra**: Celery + Redis (async tasks), Clerk (auth), Langfuse (observability)

## Quick Start

Prerequisites: Docker, Docker Compose, [just](https://github.com/casey/just)

```bash
just setup              # Create .env files from examples
# Edit backend/.env and frontend/.env with your API keys
just dev                # Build and start everything
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Langfuse: http://localhost:3001
- Flower (Celery): http://localhost:5555

## Required API Keys

| Key | Where | Purpose |
|-----|-------|---------|
| `OPENAI_API_KEY` | `backend/.env` | LLM calls via LiteLLM |
| `JINA_API_KEY` | `backend/.env` | Document embeddings |
| `CLERK_SECRET_KEY` | `backend/.env` | JWT verification |
| `VITE_CLERK_PUBLISHABLE_KEY` | `frontend/.env` | Clerk auth UI |

## Common Commands

```bash
just dev                # Build and start with hot reload
just down               # Stop services
just logs               # View all logs
just test               # Run all tests (spins up test containers)
just test -k "pattern"  # Run tests matching pattern
just lint               # Ruff linter
just check              # Lint + typecheck
just lint-frontend      # ESLint
just test-frontend      # Vitest
just db-shell           # PostgreSQL shell
just --list             # All available commands
```
