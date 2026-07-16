# Arxivian -- Public Beta Product Requirements Document

**Version:** 0.5-beta
**Last updated:** 2026-02-15
**Status:** Superseded by `docs/product/feed-prd.md` (the feed pivot). Retained as the
chat-first product-of-record and historical baseline; the pivot demotes chat from
primary interface to a scoped per-paper panel. Sections below marked "(pivot)" note where
the feed PRD departs.

---

## 1. Product Summary

Arxivian is an agentic RAG system for arXiv papers. Researchers chat with an AI agent
that can search, ingest, retrieve, summarize, and explore citations across academic
papers. The system uses a LangGraph workflow (guardrail, routing, tool execution,
grading, generation) backed by hybrid retrieval (pgvector + full-text + RRF) over a
communal knowledge base.

**Beta goal:** Ship a polished, reliable product that individual researchers can use
daily for paper discovery and analysis. Close the feature gaps between what exists and
what a user would expect from the landing page promise.

---

## 2. Target Persona

**Primary:** Individual researchers (PhD students, postdocs, independent academics)

- Works at a desktop/laptop (mobile is out of scope)
- Reads 5-20 papers per week across 2-3 arXiv categories
- Wants to quickly understand a paper's contributions, find related work, and trace
  citation chains
- Values transparency in AI reasoning (wants to see what the agent did, not just the
  answer)
- Currently uses arXiv directly, Semantic Scholar, or Google Scholar with manual PDF
  reading

**Not targeting for beta:** Research teams, enterprise/org accounts, mobile users.

---

## 3. Design Principles

1. **Chat is the primary interface.** Every feature should be accessible through
   conversation. The library and citation views are companions, not replacements.
   *(pivot: reversed -- the feed is primary; chat is a scoped per-paper panel. See
   `feed-prd.md` Design Principle 1.)*

2. **Transparency over magic.** Show the agent's reasoning steps, guardrail scores,
   retrieval attempts, and sources. Researchers trust tools they can inspect.

3. **Communal knowledge grows with use.** Every paper ingested by any user enriches the
   shared corpus. No redundant storage, no silos.

4. **Degrade gracefully.** If Redis is down, skip caching. If Langfuse is off, skip
   tracing. If a tool fails, the agent routes around it. Never block the user.

5. **Simple tier model.** Free gets 20 chats/day. Pro gets unlimited. No feature gating
   beyond that for now.

---

## 4. Current State (Pre-Beta)

### What works well

| Area | Status |
|---|---|
| Chat with streaming + thinking visualization | Complete |
| 6 agent tools (retrieve, search, ingest, summarize, citations, list) | Complete |
| LangGraph workflow with guardrail, routing, grading | Complete |
| Paper library with grid, category filter, pagination | Complete |
| Settings (LLM preferences, agent parameters) | Complete |
| Auth (Clerk JWT, Google OAuth) | Complete |
| Tier system (Free/Pro) with daily rate limiting | Complete |
| Conversation history (list, resume, delete) | Complete |
| Backend API (25 endpoints, zero TODOs) | Complete |
| Test suite (399+ tests, 80% coverage) | Complete |
| CI pipeline (lint, typecheck, test) | Complete |
| Landing page + pricing page | Complete |

### What is missing for beta

| Gap | Priority | Epic |
|---|---|---|
| Citation explorer (advertised, not built in UI) | Must | CITE |
| Paper detail view (library cards have no click-through) | Must | LIB |
| Response feedback (thumbs up/down) | Must | FEED |
| Bug report button | Must | FEED |
| Sentry error tracking (frontend + backend) | Must | OPS |
| Global rate limiting (per-IP abuse protection) | Must | OPS |
| Rate limit approaching indicator in UI | Should | CHAT |
| Better error messages for failed queries | Should | CHAT |
| Redis embedding cache (reduce Jina API costs) | Should | PERF |
| Redis ingestion lock (prevent duplicate work) | Should | PERF |
| Full-text paper search in library | Won't (use chat) | -- |
| Onboarding walkthrough | Won't (post-beta) | -- |
| Curated seed corpus | Won't (post-beta) | -- |
| Mobile responsive | Won't | -- |
| Conversation export | Won't (post-beta) | -- |
| Paper annotations | Won't | -- |
| Team/org features | Won't | -- |

---

## 5. Scope Boundary

### In scope (beta)

- Citation explorer: enhanced inline chat citations as the first step
- Paper library: detail view on card click
- In-app feedback: thumbs up/down on agent responses, bug report button
- Operational: Sentry cloud integration, global per-IP rate limiting
- Backend optimization: embedding cache, ingestion deduplication lock
- Chat UX: rate limit indicator, improved error states

### Out of scope (post-beta)

- Graph/tree visualization for citations (future expansion of citation explorer)
- Interactive onboarding walkthrough
- Pre-seeded curated paper corpus
- Full-text search across paper titles/abstracts in library
- Conversation export (markdown/PDF)
- Paper management (delete, favorites, collections)
- Mobile/tablet responsive layout
- Team features, shared libraries, collaborative annotations
- Advanced monitoring (Prometheus/Grafana dashboards)
- Infrastructure-as-code, horizontal scaling

### Already handled (not in stories)

- HTTPS/TLS and domain -- Cloudflare
- CI/CD deployment -- Coolify (auto-deploy on push)
- Database backups -- Coolify (confirm configuration)

---

## 6. Success Metrics (Beta)

> **(pivot):** The metrics below are chat-centric. Under the feed model they are replaced
> by: weekly-digest ritual (opens/week), saved -> shipped conversions (>=1/month with a
> public repo), golden-set rubric accuracy (>=85% on feasibility + code-gap), and top-10
> feed precision (<3 of 10 dismissed as "misjudged"/week). "Chat sessions per user per
> day" and "thumbs-up rate" are no longer primary. See `feed-prd.md` Section 7. Removed
> surfaces: global chat tab and conversation-history list (conversation data archived,
> not deleted).

| Metric | Target | How measured |
|---|---|---|
| Daily active users | 50+ within 4 weeks of launch | Clerk auth events |
| Chat sessions per user per day | 3+ average | usage_counters table |
| Agent response quality | 80%+ thumbs-up rate | Langfuse feedback scores |
| Error rate | < 2% of chat requests | Sentry error count / total requests |
| Paper corpus growth | 100+ papers/week organic | papers table count |
| P95 response latency (first token) | < 4 seconds | Langfuse trace durations |

---

## 7. Technical Constraints

- **LLM provider:** LiteLLM with OpenAI as default, NVIDIA NIM as alternative.
  Structured output model can differ from generation model.
- **Embeddings:** Jina (1024-dim). Embedding cache will reduce redundant API calls.
- **Database:** PostgreSQL 16 + pgvector. Single instance, no read replicas for beta.
- **Redis:** Single instance, DB 0 (RediSearch constraint for LangGraph checkpoints).
  DBs 1-2 for Celery and general cache.
- **Search:** Hybrid (vector + full-text + RRF). No external search engine.
- **Deployment:** VPS with Coolify orchestration, Cloudflare for edge.
- **Auth:** Clerk (Google OAuth only). No email/password for beta.

---

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Jina API costs scale with user growth | High (embedding every query + chunk) | Embedding cache (PERF epic) reduces repeat calls |
| Concurrent ingestion of same paper | Medium (wasted compute + potential race conditions) | Ingestion lock (PERF epic) |
| LLM hallucination in responses | High (erodes researcher trust) | Guardrail + grading nodes already in place; feedback loop via thumbs down |
| Cold start for new users (empty library) | Medium (unclear value prop) | Suggestion chips guide first interactions; daily ingest populates corpus |
| Single VPS failure | High (total downtime) | Coolify health checks + auto-restart; Cloudflare caching for static assets |

---

## 9. Document Index

| Document | Path | Purpose |
|---|---|---|
| User Stories | `docs/product/user-stories.md` | Epics, stories, acceptance criteria |
| Langfuse Setup | `docs/langfuse-setup.md` | Observability configuration guide |
| Redis Cache Design | `docs/redis-embedding-cache-ingestion-lock.md` | Technical design for PERF epic |
