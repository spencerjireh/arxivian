# Roadmap

## Overview

A research paper assistant powered by LangGraph with hybrid retrieval, multi-turn conversations, and extensible tooling.

**Current Status**: Core functionality complete, preparing for production MVP.

---

## Milestone 1: Production MVP (P0)

Foundation for a stable, observable, tested system ready for real usage.

### Error Recovery

_Critical fixes identified in codebase audit._

| Status | Item | Notes |
|--------|------|-------|
| [x] | Fix silent PDF parsing failures | Raise exception instead of returning error as text |
| [x] | Transaction wrapper for paper ingestion | Rollback on partial failures, prevent orphaned chunks |
| [x] | Orphaned record cleanup | On-demand cleanup endpoint at POST /api/v1/admin/cleanup |
| [x] | Retry logic for arXiv API calls | 3 attempts with exponential backoff via tenacity |
| [x] | Retry logic for PDF downloads | 3 attempts with exponential backoff via tenacity |
| [x] | Idempotency tokens for ingestion | Prevent duplicate processing via idempotency_key parameter |
| [x] | Duplicate paper detection | Row-level locking prevents race conditions |

### Request Lifecycle

_Ensure requests can be bounded and cancelled._

| Status | Item | Notes |
|--------|------|-------|
| [x] | Agent execution timeout | Max 3 minutes per request, configurable via `timeout_seconds` |
| [x] | LLM call timeouts | Explicit timeout on generate calls (60s default) |
| [x] | Client disconnect detection | Stop work when SSE client closes connection |
| [x] | Task cleanup on disconnect | Cancel running async tasks, release resources |
| [x] | User cancellation endpoint | POST /conversations/{id}/cancel |
| [x] | Make max_iterations configurable | Expose in StreamRequest schema |

### Observability

| Status | Item | Notes |
|--------|------|-------|
| [x] | Langfuse SDK integration | Basic setup with CallbackHandler and TracedLLMClient |
| [x] | Session and user context in traces | session_id/user_id passed to CallbackHandler |
| [x] | Trace ID in response metadata | Enables frontend feedback submission |
| [x] | Feedback endpoint | POST /api/v1/feedback with trace_id linking |
| [x] | Unified trace hierarchy | LLM generations nested under graph trace via contextvars |
| [x] | Custom Langfuse scores | guardrail_score, retrieval_attempts as langfuse.score() calls |

### Testing

| Status | Item | Notes |
|--------|------|-------|
| [x] | Unit tests for services and repositories |  |
| [x] | Integration tests for API endpoints | 92 tests covering all 8 routers |
| [ ] | Agent flow tests with mocked LLM | |

### Authentication

_Using Clerk with Google OAuth._

| Status | Item | Notes |
|--------|------|-------|
| [x] | Clerk integration | ClerkProvider in frontend, PyJWT verification in backend |
| [x] | Google OAuth setup | OAuthButtons component with oauth_google strategy |
| [x] | User model and migrations | User model with clerk_id, auto-sync via get_or_create |
| [x] | JWT verification middleware | AuthService with JWKS validation, RS256 signature checks |
| [x] | Auth dependencies | CurrentUserRequired/CurrentUserOptional type aliases |
| [x] | Protected API routes | All 10 routers use CurrentUserRequired |

### Usage Limits

_Daily limits on expensive operations for free-tier users._

| Status | Item | Notes |
|--------|------|-------|
| [x] | Usage counter model | Daily counters per user with atomic UPSERT increments |
| [x] | Query limit enforcement | 429 before stream starts, configurable via DAILY_QUERY_LIMIT |
| [x] | Ingest limit enforcement | 429 before ingestion, configurable via DAILY_INGEST_LIMIT |

### Security Hardening

| Status | Item | Notes |
|--------|------|-------|
| [ ] | Input sanitization audit | |
| [ ] | Prompt injection mitigation | |

---

## Milestone 2: User-Ready Release (P1)

Improved retrieval quality, reliability, and deployment readiness.

### User Features

| Status | Item | Notes |
|--------|------|-------|
| [x] | Conversations belong to users | user_id filtering on all conversation queries |
| [x] | User preferences persistence | Model, repository, and API all exist |

### Onboarding UX

| Status | Item | Notes |
|--------|------|-------|
| [x] | Empty state for new users | EmptyConversationState component |
| [x] | Example queries | SuggestionChips component |

### Retrieval Improvements

| Status | Item | Notes |
|--------|------|-------|
| [ ] | Query expansion | Generate multiple search queries from user input |
| [ ] | Re-ranking with cross-encoder | |
| [ ] | Multi-query retrieval | Combine results from expanded queries |

### Reliability

| Status | Item | Notes |
|--------|------|-------|
| [ ] | Rate limiting per IP | Basic per-IP rate limiting |
| [ ] | Graceful degradation when LLM unavailable | |

### User Feedback

| Status | Item | Notes |
|--------|------|-------|
| [x] | Feedback model and API | POST /api/v1/feedback with trace_id linking |
| [x] | Link feedback to conversation turns | trace_id linking exists |
| [ ] | Feedback UI in frontend | Simple thumbs up/down on responses |

### E2E Testing

_Deferred from P0. Use mocked LLM responses for determinism._

| Status | Item | Notes |
|--------|------|-------|
| [ ] | Playwright test infrastructure | Test containers for Postgres, mocked external APIs |
| [ ] | E2E: Conversation flow | Send query, receive streamed response, view sources |
| [ ] | E2E: Paper ingestion | Search arXiv, ingest paper, verify in library |
| [ ] | E2E: Conversation history | Load past conversations, continue chat |
| [ ] | E2E: Error states | Graceful handling of failures in UI |

### CI/CD

| Status | Item | Notes |
|--------|------|-------|
| [ ] | GitHub Actions workflow | lint, typecheck, test, build |
| [ ] | Production deployment automation | Coolify docker-compose |

---

## Milestone 3: Automation and Advanced Features (P2)

Scheduled tasks and performance optimization.

### Scheduled Runs

| Status | Item | Notes |
|--------|------|-------|
| [x] | Celery Beat integration | Running as Docker service |
| [x] | Scheduled task: ingest papers | Daily 2am UTC via cron config |
| [x] | Scheduled task: generate weekly digests | Weekly Monday 6am UTC |

### Performance

| Status | Item | Notes |
|--------|------|-------|
| [ ] | Redis caching layer | embeddings, search results, context |
| [ ] | Connection pooling optimization | |
| [ ] | Batch embedding requests | |

---

## Backlog (P3)

Items to consider for future releases. Not prioritized.

- [ ] Multi-agent workflows (researcher, writer, critic)
- [ ] Citation network visualization
- [ ] Paper recommendation engine
- [ ] Research trend analysis
- [ ] User preference learning
- [ ] Slack/Discord/Telegram bot integration
- [ ] Time-based report generation
- [ ] Expansion to IEEE, PubMed, etc.

---

## Infrastructure Decisions

| Item | Decision |
|------|----------|
| Hosting | Coolify (self-hosted PaaS) |
| PostgreSQL | Managed via Coolify (single instance) |
| Redis | Single instance (Celery broker) |

---

## Completed

<details>
<summary>Click to expand completed items</summary>

### Core Infrastructure
- [x] FastAPI backend with async PostgreSQL + pgvector
- [x] React 19 frontend with TypeScript and Vite
- [x] Docker Compose development environment with hot reload
- [x] Alembic migrations for schema management

### Agent Architecture
- [x] LangGraph-based agent with router architecture
- [x] Guardrail node for query relevance filtering (0-100 scoring)
- [x] Dynamic tool selection via LLM router
- [x] Tool registry for extensible tool management

### Agent Tools
- [x] `retrieve_chunks` - hybrid search over paper database
- [x] `web_search` - DuckDuckGo API for recent information
- [x] `ingest_papers` - agent-triggered paper ingestion from arXiv
- [x] `list_papers` - query papers in database with filters
- [x] `arxiv_search` - search arXiv directly without ingesting
- [x] `summarize_paper` - generate paper summaries
- [x] `explore_citations` - find citing/cited papers
- [x] Parallel tool execution

### Retrieval
- [x] Hybrid search with Reciprocal Rank Fusion (RRF)
- [x] Vector search using pgvector HNSW index
- [x] Full-text search with PostgreSQL tsvector/GIN
- [x] Document grading with retry logic
- [x] Answer generation with source citations

### Embeddings and Ingestion
- [x] Jina Embeddings v3 (1024 dimensions)
- [x] arXiv API integration for paper metadata
- [x] PDF download and parsing
- [x] Section-aware text chunking
- [x] Batch embedding generation

### LLM Integration
- [x] Abstract `BaseLLMClient` interface
- [x] OpenAI client with structured outputs
- [x] Z.AI client for GLM models
- [x] Per-request provider/model selection

### Conversation Management
- [x] Multi-turn conversation persistence
- [x] Configurable conversation window
- [x] Turn metadata storage (sources, reasoning steps)

### Frontend
- [x] Real-time SSE streaming with token-by-token display
- [x] Thinking steps visualization (stepper + timeline)
- [x] Source cards with relevance scores
- [x] Advanced settings panel (provider, model, temperature, etc.)
- [x] Conversation sidebar with history
- [x] Markdown rendering with syntax highlighting
- [x] Responsive design with Framer Motion animations

### Observability
- [x] Langfuse SDK integration (v3.0.0+)
- [x] TracedLLMClient wrapper for LLM call tracing
- [x] LangGraph CallbackHandler passed to astream_events
- [x] Session and user context in CallbackHandler trace
- [x] Trace ID returned in response metadata
- [x] Feedback endpoint (POST /api/v1/feedback) for user feedback scores
- [x] Lifespan integration with graceful shutdown
- [x] Unified trace hierarchy (LLM generations nested under graph trace via contextvars)
- [x] Custom Langfuse scores (guardrail_score, retrieval_attempts)

</details>
