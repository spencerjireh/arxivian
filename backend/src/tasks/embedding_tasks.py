"""One-off re-embedding of every chunk (ARX-40).

Vectors from different embedding models are not comparable, so a model change (Jina v3
-> OpenAI text-embedding-3-small, 2026-09-22) has to rewrite `chunks.embedding` for every
row. The driver walks the table by primary key (keyset cursor) in batches, flushes each
batch, and stops at a time budget; the task commits and re-enqueues itself with the cursor
so it never trips the Celery task time limit. Not on the beat schedule: run it by hand
(`celery call src.tasks.embedding_tasks.reembed_chunks_task`) after deploying a model change.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.clients.embeddings_client import EmbeddingsClient
from src.config import get_settings
from src.database import AsyncSessionLocal
from src.factories import get_embeddings_client
from src.repositories.chunk_repository import ChunkRepository
from src.tasks.runtime import run_async
from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_BATCH_SIZE = 100
BUDGET_MARGIN_SECONDS = 60


async def reembed_chunks(
    session: AsyncSession,
    client: EmbeddingsClient,
    *,
    after_id: str | None,
    batch_size: int,
    budget_seconds: float,
) -> dict[str, Any]:
    """Re-embed chunks with id > `after_id` in `batch_size` pages until done or out of time.

    Flushes each batch; the caller owns commit. Returns the last id processed so a follow-up
    call can resume, and `done=True` once a page comes back empty.
    """
    repo = ChunkRepository(session)
    started = time.monotonic()
    updated = 0
    last_id = after_id
    while True:
        rows = await repo.list_after(after_id=last_id, limit=batch_size)
        if not rows:
            return {"updated": updated, "last_id": last_id, "done": True}

        vectors = await client.embed_documents([row.chunk_text for row in rows])
        await repo.update_embeddings(
            [(row.id, vector) for row, vector in zip(rows, vectors, strict=True)]
        )
        updated += len(rows)
        last_id = str(rows[-1].id)
        log.info("reembed_batch", updated=updated, last_id=last_id)

        if time.monotonic() - started >= budget_seconds:
            return {"updated": updated, "last_id": last_id, "done": False}


@celery_app.task(name="src.tasks.embedding_tasks.reembed_chunks_task")
def reembed_chunks_task(
    after_id: str | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> dict[str, Any]:
    """Re-embed every chunk after `after_id`; re-enqueues itself until the table is done."""
    log.info("reembed_started", after_id=after_id, batch_size=batch_size)

    async def _run() -> dict[str, Any]:
        settings = get_settings()
        budget = max(float(settings.celery_task_timeout - BUDGET_MARGIN_SECONDS), 30.0)
        async with AsyncSessionLocal() as session:
            result = await reembed_chunks(
                session,
                get_embeddings_client(),
                after_id=after_id,
                batch_size=batch_size,
                budget_seconds=budget,
            )
            await session.commit()
        return {"status": "completed", **result}

    result = run_async(_run())
    if not result["done"]:
        reembed_chunks_task.apply_async(
            kwargs={"after_id": result["last_id"], "batch_size": batch_size}
        )
    log.info("reembed_completed", **{k: v for k, v in result.items() if k != "status"})
    return result
