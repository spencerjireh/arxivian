# Roadmap

## Completed

- [x] FastAPI backend with async PostgreSQL + pgvector
- [x] React 19 frontend with TypeScript and Vite
- [x] Docker Compose development environment with hot reload
- [x] Alembic migrations for schema management
- [x] LangGraph-based agent with router architecture
- [x] Guardrail node for query relevance filtering (0-100 scoring)
- [x] Dynamic tool selection via LLM router
- [x] Tool registry for extensible tool management
- [x] `retrieve_chunks` tool - hybrid search over paper database
- [x] `web_search` tool - DuckDuckGo API for recent information
- [x] Document grading with retry logic
- [x] Answer generation with source citations
- [x] Hybrid search with Reciprocal Rank Fusion (RRF)
- [x] Vector search using pgvector HNSW index
- [x] Full-text search with PostgreSQL tsvector/GIN
- [x] Jina Embeddings v3 (1024 dimensions)
- [x] arXiv API integration for paper metadata
- [x] PDF download and parsing
- [x] Section-aware text chunking
- [x] Batch embedding generation
- [x] Abstract `BaseLLMClient` interface
- [x] OpenAI client with structured outputs
- [x] Z.AI client for GLM models
- [x] Per-request provider/model selection
- [x] Multi-turn conversation persistence
- [x] Configurable conversation window
- [x] Turn metadata storage (sources, reasoning steps)
- [x] Real-time SSE streaming with token-by-token display
- [x] Thinking steps visualization (stepper + timeline)
- [x] Source cards with relevance scores
- [x] Advanced settings panel (provider, model, temperature, etc.)
- [x] Conversation sidebar with history
- [x] Markdown rendering with syntax highlighting
- [x] Responsive design with Framer Motion animations

---

## To Do

### Agent Tools
- [ ] `ingest_papers` tool - agent can trigger paper ingestion from arXiv
- [ ] `arxiv_search` tool - search arXiv directly without ingesting
- [ ] `summarize_paper` tool - generate paper summaries
- [ ] `explore_citations` tool - find citing/cited papers

### Retrieval
- [ ] Query expansion - generate multiple search queries from user input
- [ ] Re-ranking with cross-encoder model
- [ ] Multi-query retrieval - combine results from expanded queries
- [ ] Contextual compression - extract only relevant parts of chunks

### Scheduled Runs
- [ ] Schedule model (cron expression, query, enabled flag)
- [ ] APScheduler or Celery Beat integration
- [ ] Scheduled task: ingest new papers matching saved queries
- [ ] Scheduled task: generate daily/weekly digests
- [ ] Email or webhook notifications for completed runs

### Observability (Langfuse)
- [ ] Install langfuse SDK
- [ ] Trace all LLM calls (router, grader, generator)
- [ ] Trace tool executions with input/output
- [ ] Track token usage and latency per node
- [ ] Add session and user context to traces
- [ ] Custom metrics for guardrail scores and retrieval attempts

### Metrics & Cost
- [ ] Prometheus metrics endpoint
- [ ] Request latency histograms
- [ ] Active conversations gauge
- [ ] Tool usage counters
- [ ] Error rate by endpoint
- [ ] Token usage aggregation per user/session
- [ ] Cost calculation based on model pricing
- [ ] Daily/monthly cost reports
- [ ] Budget alerts

### Testing
- [ ] Unit tests for services and repositories
- [ ] Integration tests for API endpoints
- [ ] Agent flow tests with mocked LLM responses
- [ ] Frontend component tests with Vitest
- [ ] E2E tests with Playwright

### Performance
- [ ] Redis caching layer (embeddings, search results, conversation context)
- [ ] Connection pooling optimization
- [ ] Batch embedding requests
- [ ] Response streaming optimization

### Reliability
- [ ] Rate limiting per IP/user
- [ ] Request validation and sanitization
- [ ] Graceful degradation when LLM unavailable
- [ ] Circuit breaker for external APIs
- [ ] Health check dependencies (DB, Redis, LLM)

### Security
- [ ] Input sanitization audit
- [ ] SQL injection prevention audit
- [ ] Prompt injection mitigation
- [ ] API key rotation mechanism
- [ ] Secrets management

### Authentication
- [ ] User model and migrations
- [ ] JWT-based authentication
- [ ] OAuth providers (Google, GitHub)
- [ ] Session management
- [ ] Password reset flow

### User Features
- [ ] Conversations belong to users
- [ ] Paper collections/folders per user
- [ ] Personal paper library
- [ ] Saved searches and alerts
- [ ] User preferences persistence
- [ ] Share conversations via link
- [ ] Export conversations (Markdown, PDF)
- [ ] Annotation and highlights on papers

### Monetization
- [ ] Stripe integration
- [ ] Plan model (free, pro, enterprise)
- [ ] Usage quotas per plan (messages, papers, scheduled jobs)
- [ ] Billing portal integration
- [ ] Track usage against quotas
- [ ] Soft limits with warnings
- [ ] Hard limits with graceful blocking
- [ ] Usage dashboard for users
- [ ] Admin dashboard for revenue metrics

### Advanced Agent
- [ ] Pause agent for user confirmation (human-in-the-loop)
- [ ] Tool execution approval workflow
- [ ] Resume from paused state
- [ ] Long-term memory store
- [ ] User preference learning
- [ ] Cross-conversation context
- [ ] Multi-agent workflows (researcher, writer, critic)
- [ ] Citation network visualization

### CI/CD
- [ ] GitHub Actions workflow (lint, type check, test, build, push)
- [ ] Staging environment
- [ ] Production deployment automation

### Infrastructure
- [ ] Kubernetes manifests or Helm charts
- [ ] Managed PostgreSQL
- [ ] Redis cluster
- [ ] CDN for frontend assets
- [ ] Load balancer with SSL termination

### Monitoring
- [ ] Grafana dashboards
- [ ] Alert rules (error rate, latency, availability)
- [ ] PagerDuty or Opsgenie integration
- [ ] Log aggregation

### Backlog
- [ ] Browser extension for saving papers
- [ ] Mobile app
- [ ] Paper recommendation engine
- [ ] Integration with reference managers (Zotero, Mendeley)
- [ ] LaTeX export for citations
- [ ] Paper comparison tool
- [ ] Research trend analysis
- [ ] Voice interface
- [ ] Slack/Discord bot integration
