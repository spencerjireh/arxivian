# Plan: Communal Knowledge Base

## Prerequisites

The user-tiers plan is **fully implemented**. That plan added `papers.user_id`
(FK, NOT NULL) with a per-user unique constraint `(user_id, arxiv_id)`, an
`_ownership_filter()` helper in `paper_repository.py`, and `user_id` threading
through agent tools. This plan reverses those paper-ownership parts while
keeping all tier infrastructure (rate limiting, model selection, search slots,
system user, `/me` endpoint) intact.

The dedicated `/ingest` endpoint was already removed by the tiers plan.
Ingestion happens via the chat agent's ingest tool or Celery scheduled tasks.

## Decision

Papers and chunks become a **shared, append-only knowledge base** with no user
ownership. Users own only their conversations, reports, preferences, and usage
counters. The `papers.user_id` column is renamed to `ingested_by` as a
non-functional audit trail (who contributed the paper), not an access control
boundary.

Search has no user scoping -- every query searches the entire corpus. Ingestion
deduplicates globally on `arxiv_id` (if the paper already exists, skip it).
User-facing paper deletion is removed; cleanup is an admin/ops concern.

## Rationale

- arXiv papers are public documents -- per-user walls around public knowledge
  create artificial boundaries.
- Append-only shared corpus avoids: dedup link tables, reference counting,
  deletion race conditions, and per-query ownership filtering.
- The search repository already has no user_id filter -- this plan codifies and
  extends that existing reality.
- Simpler code: ownership logic is removed rather than added.

---

## Schema Changes

### 1. Alembic Migration

Create `backend/alembic/versions/20260209_communal_knowledge_base.py`.

```
Revision message: "Make papers communal: rename user_id to ingested_by, global arxiv_id unique"
```

Steps:

1. **Rename** `papers.user_id` column to `ingested_by`.
2. **Drop** unique constraint `uq_papers_user_arxiv` (was `user_id, arxiv_id`).
3. **Add** unique constraint `uq_papers_arxiv_id` on `arxiv_id` alone (global
   dedup).
4. **Rename** index `ix_papers_user_id` to `ix_papers_ingested_by`.
5. **Rename** foreign key `fk_papers_user_id` to `fk_papers_ingested_by`.
6. **Make** `ingested_by` nullable (anonymous/system ingestions may not have a
   user; also simplifies the column's audit-only semantics).

Downgrade reverses all steps.

### 2. Paper Model (`src/models/paper.py`)

Current (line 14-21):
```python
__table_args__ = (
    UniqueConstraint("user_id", "arxiv_id", name="uq_papers_user_arxiv"),
)
user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
```

Change to:
```python
__table_args__ = (
    UniqueConstraint("arxiv_id", name="uq_papers_arxiv_id"),
)
ingested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
```

The column is renamed from `user_id` to `ingested_by` and made nullable. The
unique constraint moves from `(user_id, arxiv_id)` to just `(arxiv_id)`.

---

## Backend Changes

### 3. Paper Repository (`src/repositories/paper_repository.py`)

**Remove `_ownership_filter()`** (lines 21-26) and its import of
`get_system_user_id` from `src/tiers`. This helper was added by the tiers plan
for per-user scoping and is no longer needed for papers. (It remains in
`report_repository.py` where reports stay user-scoped.)

**`get_by_arxiv_id()`** (lines 36-46): Remove the `user_id` parameter and the
ownership filter. Query by `arxiv_id` alone.

```python
async def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
    stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**`get_by_arxiv_id_for_update()`** (lines 48-74): Remove `user_id` parameter.
Lock by `arxiv_id` alone (global uniqueness guarantees at most one row).

```python
async def get_by_arxiv_id_for_update(self, arxiv_id: str) -> Optional[Paper]:
    stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
    result = await self.session.execute(stmt.with_for_update(nowait=True))
    return result.scalar_one_or_none()
```

**`get_all()`** (lines 129-218): Remove `user_id` parameter and the
`_ownership_filter` call at line 179. All papers are visible to everyone.

**`delete_by_arxiv_id()`** (lines 239-260): Remove `user_id` parameter and
ownership filter. This method will only be called from admin/ops endpoints, not
user-facing routes.

### 4. Search Repository (`src/repositories/search_repository.py`)

**No changes.** The vector and fulltext search queries already have no user_id
filtering. This is the desired behavior.

### 5. Report Repository (`src/repositories/report_repository.py`)

**No changes.** Reports remain user-scoped -- they track what a specific user's
scheduled searches found. The `_ownership_filter` here stays.

### 6. Ingest Service (`src/services/ingest_service.py`)

**Constructor** (lines 31-47): Rename `user_id` parameter to `ingested_by`.
Semantics change from "owner" to "audit: who triggered this ingestion."

```python
def __init__(self, ..., ingested_by: Optional[str] = None):
    ...
    self.ingested_by = ingested_by
```

**`_process_single_paper()`** (lines 132-280):

- **Lines 145-151** (owner resolution): Replace ownership logic. Instead of
  resolving an "owner" and scoping lookups to them, do a global check:

  ```python
  # Global dedup -- arxiv_id is globally unique now
  existing = await self.paper_repository.get_by_arxiv_id(arxiv_id)
  if existing and not force_reprocess:
      log.debug("paper skipped (exists globally)", arxiv_id=arxiv_id)
      return None
  ```

- **Lines 205-206** (lock lookup): Remove user_id from `get_by_arxiv_id_for_update`:

  ```python
  existing_locked = await self.paper_repository.get_by_arxiv_id_for_update(arxiv_id)
  ```

- **Lines 219-232** (paper creation): Replace `"user_id": owner_id` with
  `"ingested_by": self.ingested_by` (can be None for system/anonymous
  ingestions):

  ```python
  paper_data = {
      "arxiv_id": arxiv_id,
      "ingested_by": self.ingested_by,
      "title": paper_meta.title,
      ...
  }
  ```

**`list_papers()`** (lines 354-394): Remove user_id scoping. Call
`paper_repository.get_all()` without `user_id`:

```python
papers, total = await self.paper_repository.get_all(
    offset=offset, limit=limit, query=query,
    author_filter=author, category_filter=category,
    start_date=start_date, end_date=end_date,
)
```

### 7. Service Factories (`src/factories/service_factories.py`)

**`get_ingest_service()`** (lines 72-102): Rename `user_id` parameter to
`ingested_by`. Pass through to `IngestService`:

```python
def get_ingest_service(
    db_session: AsyncSession, ingested_by: Optional[str] = None
) -> IngestService:
    ...
    return IngestService(..., ingested_by=ingested_by)
```

**`get_agent_service()`** (lines 105-183):

- Line 156-157: Update to pass `ingested_by` instead of `user_id` to
  `get_ingest_service`:
  ```python
  ingested_by_str = str(user_id) if user_id else None
  ingest_service = get_ingest_service(db_session, ingested_by=ingested_by_str) if can_ingest else None
  ```

- Lines 82, 95 (`user_id` param on `AgentService` and `build_agent_graph`):
  `user_id` is still passed for conversation ownership. It no longer flows to
  paper tools. See AgentContext changes below.

### 8. Agent Context (`src/services/agent_service/context.py`)

**Lines 131-139** (tool registration): Remove `user_id` from
`ExploreCitationsTool` and `SummarizePaperTool` construction:

```python
if paper_repository:
    self.tool_registry.register(
        ExploreCitationsTool(paper_repository=paper_repository)
    )
    self.tool_registry.register(
        SummarizePaperTool(paper_repository=paper_repository, llm_client=llm_client)
    )
```

`user_id` is still accepted by `AgentContext.__init__` -- it's used for
conversation persistence, not paper access.

### 9. Agent Tools

**`SummarizePaperTool`** (`tools/summarize_paper.py`):
- Remove `user_id` from constructor and `self.user_id`.
- Line 66: Call `get_by_arxiv_id(arxiv_id)` without `user_id`.

**`ExploreCitationsTool`** (`tools/explore_citations.py`):
- Remove `user_id` from constructor and `self.user_id`.
- Line 50: Call `get_by_arxiv_id(arxiv_id)` without `user_id`.

**`RetrieveChunksTool`** (`tools/retrieve.py`): **No changes.** Already calls
`search_service.hybrid_search()` without user_id.

**`ListPapersTool`** (`tools/list_papers.py`): **No changes needed to the tool
itself.** It calls `ingest_service.list_papers()` which will now return all
papers (the user_id scoping is removed from the service).

**`IngestPapersTool`** (`tools/ingest.py`): **No changes needed to the tool
itself.** It calls `ingest_service.ingest_papers()` which now does global dedup.

### 10. Search Service (`src/services/search_service.py`)

**No changes.** The search service has no user_id awareness. It calls the
repository methods which already search globally.

### 11. Tiers (`src/tiers.py`)

**No changes.** The tiers module is fully implemented and unaffected by this
plan. `get_system_user_id()` is still used by `report_repository.py` for report
ownership. It is no longer imported by `paper_repository.py` (removed in step
3).

---

## Router Changes

### 12. Papers Router (`src/routers/papers.py`)

**`GET /papers`** (lines 24-55): Remove `CurrentUserOptional` dependency and
`user_id` parameter. The endpoint returns all papers:

```python
@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    paper_repo: PaperRepoDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    processed_only: Optional[bool] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Literal["created_at", "published_date", "updated_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> PaperListResponse:
    papers, total = await paper_repo.get_all(
        offset=offset, limit=limit, processed_only=processed_only,
        category_filter=category, author_filter=author,
        start_date=start_date, end_date=end_date,
        sort_by=sort_by, sort_order=sort_order,
    )
    ...
```

**`GET /papers/{arxiv_id}`** (lines 58-69): Remove `CurrentUserOptional` and
`user_id`. Call `get_by_arxiv_id(arxiv_id)` without scoping.

**`DELETE /papers/{arxiv_id}`** (lines 72-95): **Remove this endpoint entirely**
from the user-facing router. Paper deletion becomes admin-only via the existing
ops router. If needed, add a `DELETE /ops/papers/{arxiv_id}` behind API key
auth.

### 13. Stream Router (`src/routers/stream.py`)

**No changes.** `user_id` is still passed to `get_agent_service` for
conversation ownership and usage tracking. It no longer affects paper/search
scoping (that was already the case at the search layer).

### 14. Ingest Router

**Already removed.** The dedicated `/ingest` endpoint was removed by the tiers
plan. Ingestion happens via the chat agent's ingest tool (counted as 1 chat) or
Celery scheduled tasks. No changes needed.

### 15. Ops Router (`src/routers/ops.py`)

**Optional: Add paper delete endpoint for admin use:**

```python
@router.delete("/papers/{arxiv_id}")
async def delete_paper(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    db: DbSession,
    _api_key: ApiKeyCheck,
) -> DeletePaperResponse:
    ...
```

This is behind API key auth, for ops use only.

### 16. Celery Tasks

**`ingest_tasks.py`**: Keep `user_id` as the task parameter name (changing it
would break in-flight tasks during deployment). Pass it as `ingested_by` to the
ingest service factory:

```python
service = get_ingest_service(session, ingested_by=user_id)
```

The `_persist_report` call still uses `user_id` for report ownership (reports
are user-scoped, papers are not).

**`scheduled_tasks.py`**: No changes needed. Passes `user_id` to
`ingest_papers_task` which is still the correct behavior.

---

## Frontend Changes

### 17. Library Page (`frontend/src/pages/LibraryPage.tsx`)

- Remove the delete functionality: remove `useDeletePaper` import and
  `handleDelete`/`deletePaper` state.
- Remove `onDelete` and `isDeleting` props from `PaperCard`.
- Update empty state text from "Papers will appear here once ingested via chat"
  to "No papers in the knowledge base yet".

### 18. PaperCard Component (`frontend/src/components/library/PaperCard.tsx`)

- Remove the delete button, confirmation dialog, and all associated state
  (`confirmDelete`, `onDelete`, `isDeleting` props).
- Simplify to a read-only display card.

### 19. Papers API (`frontend/src/api/papers.ts`)

- Remove `deletePaper` function and `useDeletePaper` hook.
- Keep `fetchPapers` and `usePapers` (list endpoint still exists, just unscoped
  now).

### 20. Types (`frontend/src/types/api.ts`)

- Remove `DeletePaperResponse` interface (delete endpoint removed from user
  API).
- `PaperListItem` is unchanged (never had `user_id`).

---

## Test Changes

### 21. Unit Tests

Tests that mock paper repository methods with `user_id` need updating:

- `tests/unit/services/test_ingest_service.py`: Change `user_id` references to
  `ingested_by`. Remove ownership-scoped assertions in dedup tests.
- Any test that calls `paper_repo.get_by_arxiv_id(arxiv_id, user_id=...)` needs
  the `user_id` kwarg removed.
- Any test that calls `paper_repo.get_all(..., user_id=...)` needs the
  `user_id` kwarg removed.

### 22. API Tests

- `tests/api/routers/test_papers_router.py`: Remove tests for user-scoped
  paper visibility. Add/update test that list endpoint returns all papers
  regardless of auth status. Remove delete endpoint tests (or move to ops router
  tests).
- `tests/api/routers/test_ingest_router.py`: Update mock expectations for
  `ingested_by` instead of `user_id`.
- `tests/api/routers/test_stream_router.py`: No changes expected (stream tests
  already don't test paper scoping).

### 23. Integration Tests

- `tests/integration/repositories/test_paper_repository.py`: Remove tests for
  `_ownership_filter`. Update tests to use `ingested_by` column. Add test for
  global `arxiv_id` uniqueness constraint.

---

## Migration Safety

- The column rename (`user_id` -> `ingested_by`) and constraint changes should
  be done in a single migration.
- Existing data is preserved -- the backfilled system user values remain as
  `ingested_by` audit entries.
- The migration is backwards-incompatible with old code (column rename), so
  deploy code + migration together.

## Files Changed Summary

| File | Action |
|------|--------|
| `alembic/versions/20260209_communal_knowledge_base.py` | **New** migration |
| `src/models/paper.py` | Rename `user_id` -> `ingested_by`, change constraint |
| `src/repositories/paper_repository.py` | Remove `_ownership_filter`, remove `user_id` params |
| `src/services/ingest_service.py` | Rename `user_id` -> `ingested_by`, remove scoped lookups |
| `src/factories/service_factories.py` | Rename `user_id` -> `ingested_by` in ingest factory |
| `src/services/agent_service/context.py` | Remove `user_id` from paper tool construction |
| `src/services/agent_service/tools/summarize_paper.py` | Remove `user_id` |
| `src/services/agent_service/tools/explore_citations.py` | Remove `user_id` |
| `src/routers/papers.py` | Remove auth deps, remove delete endpoint |
| `src/routers/ops.py` | Add admin delete endpoint (optional) |
| `src/schemas/papers.py` | Remove `DeletePaperResponse` (or keep for ops) |
| `frontend/src/pages/LibraryPage.tsx` | Remove delete functionality |
| `frontend/src/components/library/PaperCard.tsx` | Remove delete UI |
| `frontend/src/api/papers.ts` | Remove delete API |
| `frontend/src/types/api.ts` | Remove `DeletePaperResponse` |
| `tests/unit/services/test_ingest_service.py` | Update mocks |
| `tests/api/routers/test_papers_router.py` | Update/remove scoping tests |
| `tests/api/routers/test_ingest_router.py` | Update mock expectations |
| `tests/integration/repositories/test_paper_repository.py` | Update ownership tests |

## Order of Implementation

1. Migration + model change (schema)
2. Repository changes (remove ownership filter)
3. Service changes (ingest_service, factories)
4. Tool changes (summarize, explore_citations, context)
5. Router changes (papers, ops)
6. Frontend changes (library page, paper card, API)
7. Test updates (unit, API, integration)

Each step can be verified independently before moving to the next.
