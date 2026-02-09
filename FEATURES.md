# Features

## Agent System

- [x] LangGraph workflow: guardrail -> router -> executor -> grading -> generation
- [x] Tool registry with parallel execution
- [x] Tools: `retrieve_chunks`, `arxiv_search`, `ingest_papers`, `list_papers`, `summarize_paper`, `explore_citations`
- [x] Guardrail node with relevance scoring (configurable threshold)
- [x] Document grading with retry logic
- [x] Streaming responses via SSE
- [x] Agent flow tests with mocked LLM (guardrail, tools, executor, edges)
- [ ] Query expansion / multi-query retrieval
- [ ] Re-ranking with cross-encoder

## Ingestion & Retrieval

- [x] arXiv API integration with retry logic (tenacity)
- [x] PDF download, parsing, section-aware chunking
- [x] Jina Embeddings v3 (1024d), batch processing
- [x] Hybrid search: pgvector HNSW + full-text tsvector/GIN with RRF
- [x] Dedup with row-level locking
- [x] Celery async ingestion with idempotency
- [x] Transaction rollback on partial failures
- [x] Communal knowledge base -- shared corpus, no per-user paper ownership

## LLM

- [x] LiteLLM with model prefix routing (e.g. `openai/gpt-4o-mini`)
- [x] Langfuse tracing via LiteLLM global callbacks
- [x] Structured outputs
- [ ] Provider fallback routing (LiteLLM Router)
- [ ] Cost tracking per request via `litellm.completion_cost()`

## Auth & Tiers

- [x] Clerk JWT auth with Google OAuth
- [x] User model with auto-sync via `get_or_create`
- [x] User tiers (free/pro) with per-tier rate limiting
- [x] Per-tier model gating
- [x] Daily usage counters (queries, ingestion) with 429 enforcement
- [ ] IP-based rate limiting for unauthenticated routes

## Conversations

- [x] Multi-turn persistence with configurable history window
- [x] Turn metadata storage (sources, reasoning steps)
- [x] User-scoped conversations
- [x] Execution timeout (3 min default) and client disconnect detection
- [x] User cancellation endpoint

## Scheduled Tasks

- [x] Celery Beat with worker + beat containers
- [x] Scheduled paper ingestion (daily, configurable cron)
- [ ] Scheduled report generation (report model/router exist, beat schedule not configured)
- [x] Orphaned record cleanup task

## Observability

- [x] Langfuse SDK integration with unified trace hierarchy
- [x] Session and user context in traces
- [x] Trace ID in response metadata for feedback linking
- [x] Custom Langfuse scores (guardrail_score, retrieval_attempts)
- [x] Structured logging with request ID correlation
- [x] Feedback endpoint (POST /api/v1/feedback)

## Security

- [x] Prompt injection mitigation (regex scanning, guardrail, defensive prompts)
- [x] API key auth for ops/admin endpoints
- [ ] Input sanitization audit

## Frontend

- [x] SSE streaming with token-by-token display
- [x] Thinking steps visualization
- [x] Source cards with relevance scores
- [x] Conversation sidebar with history
- [x] Library page (paper browser)
- [x] Settings page with tier-gated model selector
- [x] Landing page with GSAP animations
- [x] Markdown rendering with syntax highlighting
- [ ] Feedback UI (thumbs up/down on responses)

## Testing & CI

- [x] ~466 tests across unit, API, and integration suites
- [x] GitHub Actions: ruff, ty, unit/API tests, eslint, tsc, vitest
- [x] Pre-commit hooks: trailing whitespace, detect-secrets, ruff, eslint
- [x] Dedicated test DB (port 5433) with Docker test profile
- [ ] E2E tests (Playwright)
- [ ] Production deployment automation

## Infrastructure

- [x] Docker Compose with dev/prod/test profiles
- [x] Hot reload for backend (uvicorn) and frontend (Vite HMR)
- [x] PostgreSQL 16 + pgvector, Redis, Flower, Langfuse
- [x] Alembic migrations
- [ ] Redis caching layer (embeddings, search results)
- [ ] Connection pooling optimization

## Ideas / Backlog

- Multi-agent workflows (researcher, writer, critic)
- Citation network visualization
- Paper recommendation engine
- Research trend analysis
- Expansion to IEEE, PubMed, etc.
- Slack/Discord bot integration
- Graceful degradation when LLM unavailable
