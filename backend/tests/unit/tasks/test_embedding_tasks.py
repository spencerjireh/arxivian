"""Tests for the one-off chunk re-embedding driver (ARX-40)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.tasks.embedding_tasks import reembed_chunks


def _rows(start: int, n: int):
    return [
        SimpleNamespace(id=f"id-{i:04d}", chunk_text=f"text {i}") for i in range(start, start + n)
    ]


def _client():
    client = AsyncMock()
    client.embed_documents.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    return client


@pytest.mark.unit
class TestReembedChunks:
    async def test_pages_by_keyset_until_empty(self):
        repo = AsyncMock()
        repo.list_after.side_effect = [_rows(0, 3), _rows(3, 2), []]

        with patch("src.tasks.embedding_tasks.ChunkRepository", return_value=repo):
            result = await reembed_chunks(
                AsyncMock(), _client(), after_id=None, batch_size=3, budget_seconds=600
            )

        assert result == {"updated": 5, "last_id": "id-0004", "done": True}
        assert [c.kwargs for c in repo.list_after.await_args_list] == [
            {"after_id": None, "limit": 3},
            {"after_id": "id-0002", "limit": 3},
            {"after_id": "id-0004", "limit": 3},
        ]
        first_update = repo.update_embeddings.await_args_list[0].args[0]
        assert [chunk_id for chunk_id, _ in first_update] == ["id-0000", "id-0001", "id-0002"]
        assert all(len(v) == 1024 for _, v in first_update)

    async def test_stops_at_time_budget_and_returns_cursor(self):
        repo = AsyncMock()
        repo.list_after.side_effect = [_rows(0, 2), _rows(2, 2), []]

        with patch("src.tasks.embedding_tasks.ChunkRepository", return_value=repo):
            result = await reembed_chunks(
                AsyncMock(), _client(), after_id="id-before", batch_size=2, budget_seconds=0
            )

        assert result == {"updated": 2, "last_id": "id-0001", "done": False}
        repo.list_after.assert_awaited_once_with(after_id="id-before", limit=2)

    async def test_empty_table_is_done_with_original_cursor(self):
        repo = AsyncMock()
        repo.list_after.return_value = []
        client = _client()

        with patch("src.tasks.embedding_tasks.ChunkRepository", return_value=repo):
            result = await reembed_chunks(
                AsyncMock(), client, after_id="x", batch_size=10, budget_seconds=600
            )

        assert result == {"updated": 0, "last_id": "x", "done": True}
        client.embed_documents.assert_not_awaited()
