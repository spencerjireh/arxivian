# Implementation Plan: `list_papers` Agent Tool

## Purpose

Add a `list_papers` tool that allows the agent to query papers stored in the database. Handles questions like "what papers do you have?" or "list papers about transformers".

## Files to Modify (4 files)

| File | Action |
|------|--------|
| `backend/src/services/ingest_service.py` | Add `list_papers()` method |
| `backend/src/services/agent_service/tools/list_papers.py` | Create tool |
| `backend/src/services/agent_service/tools/__init__.py` | Export |
| `backend/src/services/agent_service/context.py` | Register tool |

---

## Step 1: Add `list_papers()` to IngestService

**File:** `backend/src/services/ingest_service.py`

Add method that queries `paper_repository` with filters:

```python
async def list_papers(
    self,
    query: str | None = None,
    author: str | None = None,
    categories: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    List papers with optional filters.

    Args:
        query: Search in title/abstract (ILIKE)
        author: Filter by author name (JSONB contains)
        categories: Filter by arXiv categories (JSONB overlap)
        start_date: Published after (YYYY-MM-DD)
        end_date: Published before (YYYY-MM-DD)
        limit: Max papers to return (default 20)
        offset: Pagination offset

    Returns:
        Tuple of (papers list, total count)
    """
```

**Implementation notes:**
- Use SQLAlchemy query on `Paper` model
- `query`: `Paper.title.ilike(f"%{query}%") | Paper.abstract.ilike(f"%{query}%")`
- `author`: `Paper.authors.contains([author])` (JSONB)
- `categories`: `Paper.categories.overlap(categories)` (JSONB)
- `start_date`/`end_date`: filter on `Paper.published_date`
- Return total count via `select(func.count(...))` before applying limit/offset
- Return paper dicts with: arxiv_id, title, authors, abstract, categories, published_date, pdf_url

---

## Step 2: Create ListPapersTool

**File:** `backend/src/services/agent_service/tools/list_papers.py` (new)

Follow pattern from `retrieve.py`:

```python
"""List papers tool for querying paper database."""

from typing import List, Optional

from src.services.ingest_service import IngestService
from src.utils.logger import get_logger
from .base import BaseTool, ToolResult

log = get_logger(__name__)


class ListPapersTool(BaseTool):
    """Tool for listing papers in the knowledge base."""

    name = "list_papers"
    description = (
        "List research papers stored in the knowledge base. "
        "Use when the user asks what papers are available, "
        "or wants to browse papers by topic, author, or date. "
        "Returns paper metadata, not content - use retrieve_chunks for content search."
    )

    def __init__(self, ingest_service: IngestService):
        self.ingest_service = ingest_service

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for title/abstract",
                },
                "author": {
                    "type": "string",
                    "description": "Filter by author name",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by arXiv categories (e.g., cs.LG, cs.AI)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Papers published after (YYYY-MM-DD)",
                },
                "end_date": {
                    "type": "string",
                    "description": "Papers published before (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max papers to return (default 20, max 50)",
                    "default": 20,
                },
            },
            "required": [],
        }

    async def execute(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        **kwargs,
    ) -> ToolResult:
        limit = min(limit, 50)

        log.debug("list_papers executing", query=query, author=author, limit=limit)

        try:
            papers, total = await self.ingest_service.list_papers(
                query=query,
                author=author,
                categories=categories,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

            result = {
                "total_count": total,
                "returned": len(papers),
                "papers": papers,
            }

            log.debug("list_papers completed", total=total, returned=len(papers))

            return ToolResult(success=True, data=result, tool_name=self.name)

        except Exception as e:
            log.error("list_papers failed", error=str(e))
            return ToolResult(success=False, error=str(e), tool_name=self.name)
```

---

## Step 3: Export from tools package

**File:** `backend/src/services/agent_service/tools/__init__.py`

Add import and export:
```python
from .list_papers import ListPapersTool
# Add to __all__: "ListPapersTool"
```

---

## Step 4: Register tool in AgentContext

**File:** `backend/src/services/agent_service/context.py`

Update import:
```python
from .tools import ToolRegistry, RetrieveChunksTool, WebSearchTool, IngestPapersTool, ListPapersTool
```

Register tool (after IngestPapersTool registration):
```python
if ingest_service:
    self.tool_registry.register(IngestPapersTool(ingest_service=ingest_service))
    self.tool_registry.register(ListPapersTool(ingest_service=ingest_service))
```

---

## Return Format

```python
{
    "total_count": 156,
    "returned": 20,
    "papers": [
        {
            "arxiv_id": "2301.00001",
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", ...],
            "abstract": "The dominant sequence transduction models...",
            "categories": ["cs.CL", "cs.LG"],
            "published_date": "2017-06-12",
            "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf"
        }
    ]
}
```

---

## Validation

1. Run `uv run ruff check src/` - no new errors
2. Run `uv run pyright` on modified files - no errors
3. Test queries:
   - No filters (list all)
   - Query filter ("transformer")
   - Author filter
   - Category filter
   - Date range filter
   - Combined filters
