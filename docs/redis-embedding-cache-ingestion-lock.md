# Design Doc: Redis Embedding Cache & Ingestion Lock

**Status:** Draft
**Author:** --
**Date:** 2026-02-15

## Problem Statement

The backend makes redundant external API calls that cost money and add latency:

1. **Duplicate embedding computations.** Every search query and agent retrieval calls
   Jina AI to generate a 1024-dim embedding vector. The same query text always produces
   the same vector, yet we recompute it on every request. Each call costs ~200-500ms
   of latency plus Jina API usage charges.

2. **Wasted work on concurrent paper ingestion.** When two Celery workers (or a
   scheduled task and a manual ingest) process the same arXiv paper simultaneously,
   both download the PDF, parse it, chunk it, and call Jina `embed_documents()` before
   the database row lock detects the duplicate. One worker's entire pipeline is thrown
   away -- wasting arXiv rate-limit budget, Jina API spend, and compute time.

## Goals

- Eliminate redundant Jina `embed_query()` calls for repeated search queries.
- Prevent concurrent workers from processing the same paper simultaneously.
- No new infrastructure. Use the existing Redis instance (DB 2) already wired into
  `app.state.redis` and `RedisDep`.
- Minimal code footprint. Changes scoped to two files.

## Non-Goals

- Caching LLM responses (non-deterministic, context-dependent).
- Caching paper metadata or search results (PostgreSQL serves these fine).
- Migrating rate limiting to Redis (current DB approach is sufficient at this scale).
- Caching `embed_documents()` (one-time bulk operations with near-zero hit rate).

## Current State

### Redis DB allocation

| DB | Purpose | Status |
|----|---------|--------|
| 0 | Celery broker + LangGraph checkpoints (RediSearch constraint) | Active |
| 1 | Celery result backend | Active |
| 2 | General purpose (`app.state.redis` / `RedisDep`) | Wired up, unused |

### Embedding call path

```
User query
  -> AgentService.stream()
    -> retrieve_chunks tool
      -> SearchService.hybrid_search()
        -> JinaEmbeddingsClient.embed_query()    <-- HTTP POST to api.jina.ai
          -> 200-500ms latency, Jina API cost per call
```

`embed_query()` is deterministic: same input text, same model, same 1024 floats.

### Ingestion call path

```
ingest_papers_task (Celery)
  -> IngestService.ingest_papers()
    -> _process_single_paper() per paper:
        1. paper_repository.get_by_arxiv_id()        ~1ms     (quick check)
        2. arxiv_client.download_pdf()                ~5-30s   (expensive)
        3. pdf_parser.parse_pdf()                     ~1-5s    (expensive)
        4. chunking_service.chunk_document()           <1s
        5. embeddings_client.embed_documents()         ~2-10s  (expensive, costs $)
        6. session.begin_nested()                               (transaction starts HERE)
        7. get_by_arxiv_id_for_update()                         (row lock, duplicate check)
        8. Insert paper + chunks
        9. Commit
```

The row lock at step 7 catches duplicates, but steps 2-5 already executed. All that
work (PDF download, parsing, embedding) is wasted on the losing worker.

---

## Design

### 1. Embedding Cache

#### Approach

Cache-aside pattern inside `JinaEmbeddingsClient.embed_query()`. The cache is
transparent to all callers -- no interface changes, no dependency changes.

#### Key schema

```
embed:{model}:{sha256(query_text)}
```

Including the model name in the key means a model upgrade (e.g., `jina-embeddings-v3`
to `v4`) naturally invalidates all cached entries without manual intervention.

#### Value format

JSON-encoded list of floats. A 1024-dim float vector serializes to ~8KB of JSON.
`msgpack` or raw bytes would be more compact but adds a dependency for negligible
gain at this data size.

#### TTL

**48 hours.** Rationale:
- Embeddings from a fixed model version never change (could be infinite TTL).
- But we don't want years of stale queries accumulating in Redis memory.
- 48h covers the pattern of "user asks similar questions across sessions over a day
  or two" without unbounded growth.

#### Flow

```
embed_query(query):
    key = f"embed:{self.model}:{sha256(query)}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    embedding = await self._call_jina(query)     # existing HTTP call
    await redis.set(key, json.dumps(embedding), ex=172800)
    return embedding
```

#### Redis dependency injection

`JinaEmbeddingsClient` is currently a singleton created at startup in
`factories/client_factories.py`. It has no Redis reference. Two options:

**Option A -- Pass Redis at construction time.** Add `redis: Redis | None = None` to
`__init__`. The factory sets it from `app.state.redis`. Celery workers (which also
embed during ingestion) would pass `None`, disabling the cache -- acceptable since
ingestion embeddings are unique per chunk and not worth caching.

**Option B -- Accept Redis per call.** Add `redis: Redis | None = None` parameter to
`embed_query()`. Callers that have access to Redis (via `RedisDep`) pass it through.
More explicit but requires changing caller signatures.

**Recommendation: Option A.** Keeps the call interface unchanged. Celery workers skip
the cache naturally (they don't have `app.state.redis`). The `SearchService` and agent
tools get caching for free without code changes.

#### Files changed

| File | Change |
|------|--------|
| `clients/embeddings_client.py` | Add Redis param, cache logic in `embed_query()` |
| `factories/client_factories.py` | Pass `app.state.redis` to client constructor |

#### Memory impact

Worst case estimate: 1000 unique queries cached * 8KB per embedding = **~8MB**. Negligible
relative to Redis capacity.

#### Failure mode

If Redis is down or the GET/SET fails, fall through to calling Jina directly. The cache
is an optimization, not a requirement. Wrap Redis operations in try/except, log warning
on failure, proceed without cache.

---

### 2. Ingestion Lock

#### Approach

Redis `SET NX` (set-if-not-exists) as a distributed lock per arXiv paper ID.
Acquired before any expensive work begins. If the lock is already held, the paper
is skipped -- another worker is handling it.

#### Key schema

```
ingest_lock:{arxiv_id}
```

#### TTL

**600 seconds (10 minutes).** Rationale:
- Matches the Celery `task_time_limit` of 600s.
- A normal paper processes in 10-60 seconds. 600s is a generous safety margin.
- If a worker crashes mid-processing, the lock auto-expires and the paper can be
  retried by the next scheduled run or manual trigger.

#### Flow

```
_process_single_paper(paper_meta, force_reprocess):
    arxiv_id = paper_meta.arxiv_id
    lock_key = f"ingest_lock:{arxiv_id}"

    # Attempt to acquire lock
    acquired = await redis.set(lock_key, "1", nx=True, ex=600)
    if not acquired:
        log.info("paper locked by another worker", arxiv_id=arxiv_id)
        return None

    try:
        # ... existing processing pipeline (download, parse, chunk, embed, store)
    finally:
        await redis.delete(lock_key)
```

#### `force_reprocess` behavior

When `force_reprocess=True`, the lock is still acquired. This prevents two concurrent
force-reprocess requests from duplicating work. The lock doesn't check whether the
paper exists -- it only prevents concurrent processing of the same `arxiv_id`.

#### Redis dependency injection

`IngestService` needs a Redis client. Two paths:

**API-triggered ingestion** (via `routers/ops.py` or agent `ingest_papers` tool):
The service is constructed via `get_ingest_service()` in `factories/service_factories.py`.
Add an optional `redis` parameter, passed from the request context.

**Celery-triggered ingestion** (via `ingest_tasks.py`):
The task creates its own `IngestService` inside `_run()`. It needs a standalone Redis
connection. Create one from `settings.redis_url` at the start of the task, close it
at the end. Alternatively, initialize a module-level async Redis client in the Celery
worker process.

**Recommendation:** Add `redis: Redis | None = None` to `IngestService.__init__()`.
When `None`, skip locking (graceful degradation). Wire it through both paths:
- API path: `get_ingest_service(db, redis=request.app.state.redis)`
- Celery path: create a short-lived `Redis.from_url()` connection in the task

#### Files changed

| File | Change |
|------|--------|
| `services/ingest_service.py` | Add Redis param, lock acquire/release in `_process_single_paper()` |
| `factories/service_factories.py` | Accept and forward optional Redis param |
| `tasks/ingest_tasks.py` | Create Redis connection, pass to `IngestService` |
| `dependencies.py` | Update `get_ingest_service_dep` to pass Redis |

#### Failure mode

- Redis down: `set(..., nx=True)` raises an exception. Catch it, log a warning, proceed
  without locking. Falls back to the existing database row lock at step 7 -- less
  efficient but still correct.
- Worker crashes mid-processing: TTL expires after 600s, paper becomes available for
  retry. No manual intervention needed.
- Lock held but worker is slow (not crashed): The TTL must be >= the longest realistic
  processing time. 600s matches the Celery task hard timeout, so a lock can never
  outlive its owning task.

---

## Testing Strategy

### Embedding cache

**Unit tests:**
- Cache miss: verify Jina API is called, result is stored in Redis.
- Cache hit: verify Jina API is NOT called, result is returned from Redis.
- Redis failure: verify Jina API is called as fallback, no exception raised.
- Key format: verify model name and query hash are in the key.

**Mocking:** Use `fakeredis.aioredis` for an in-memory Redis stub. Mock the HTTP
call to Jina with `httpx.MockTransport` or `respx`.

### Ingestion lock

**Unit tests:**
- Lock acquired: verify processing proceeds normally, lock is released after.
- Lock already held: verify paper is skipped (returns `None`), no PDF download.
- Lock released on exception: verify `finally` block deletes the key even on failure.
- `force_reprocess` with lock: verify lock is still acquired.
- Redis failure: verify processing continues without lock (fallback).

**Integration tests:**
- Simulate concurrent ingestion of the same `arxiv_id` using two async tasks.
  Verify only one processes the paper, the other skips.

---

## Rollout

Both features degrade gracefully when Redis is unavailable (fall through to existing
behavior). No feature flags needed. No migration. No schema changes.

1. Implement embedding cache in `embeddings_client.py`.
2. Implement ingestion lock in `ingest_service.py`.
3. Update factories and dependencies to wire Redis through.
4. Add unit tests.
5. Add integration test for concurrent ingestion.
6. Deploy. Monitor via existing structlog for cache hit/miss rates and lock skip events.

---

## Open Questions

1. **Should Celery workers share the `app.state.redis` singleton or create their own
   connections?** Celery workers run in a separate process from the FastAPI app. They
   need their own Redis client. A short-lived connection per task is simplest but adds
   connection overhead. A process-level singleton (initialized via Celery worker signal)
   would be more efficient for workers processing many papers.

2. **Should `embed_documents()` also be cached?** Current recommendation is no --
   chunk texts are unique per paper and ingestion is a one-time operation. Cache hit
   rate would be near zero. Revisit if papers are frequently re-ingested.

3. **Should the ingestion lock value contain worker metadata?** Storing the Celery
   task ID or worker hostname in the lock value (instead of `"1"`) would help with
   debugging ("which worker holds the lock?") at no additional cost.
