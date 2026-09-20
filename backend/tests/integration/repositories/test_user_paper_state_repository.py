"""Integration tests for UserPaperStateRepository (real test DB)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.repositories.paper_repository import PaperRepository
from src.repositories.user_paper_state_repository import UserPaperStateRepository


async def _paper(db_session, sample_paper_data, arxiv_id):
    return await PaperRepository(db_session).create({**sample_paper_data, "arxiv_id": arxiv_id})


@pytest.mark.asyncio
async def test_upsert_updates_in_place(db_session, sample_paper_data, created_user):
    repo = UserPaperStateRepository(db_session)
    paper = await _paper(db_session, sample_paper_data, "s-1")

    first = await repo.upsert(
        user_id=created_user.id,
        paper_id=paper.id,
        state="saved",
        repo_url=None,
        dismissal_reason=None,
    )
    second = await repo.upsert(
        user_id=created_user.id,
        paper_id=paper.id,
        state="dismissed",
        repo_url=None,
        dismissal_reason="not my area",
    )
    assert second.id == first.id
    assert second.state == "dismissed" and second.dismissal_reason == "not my area"

    assert (await repo.get(created_user.id, paper.id)).state == "dismissed"


@pytest.mark.asyncio
async def test_get_many_and_delete(db_session, sample_paper_data, created_user):
    repo = UserPaperStateRepository(db_session)
    a = await _paper(db_session, sample_paper_data, "s-a")
    b = await _paper(db_session, sample_paper_data, "s-b")
    c = await _paper(db_session, sample_paper_data, "s-c")
    for paper, state in ((a, "saved"), (b, "implementing")):
        await repo.upsert(
            user_id=created_user.id,
            paper_id=paper.id,
            state=state,
            repo_url=None,
            dismissal_reason=None,
        )

    found = await repo.get_many(created_user.id, [a.id, b.id, c.id])
    assert {pid: row.state for pid, row in found.items()} == {a.id: "saved", b.id: "implementing"}
    assert await repo.get_many(created_user.id, []) == {}

    assert await repo.delete(created_user.id, a.id) is True
    assert await repo.delete(created_user.id, a.id) is False
    assert await repo.get(created_user.id, a.id) is None


@pytest.mark.asyncio
async def test_list_for_user_excludes_dismissed_newest_first(
    db_session, sample_paper_data, created_user
):
    repo = UserPaperStateRepository(db_session)
    papers = [await _paper(db_session, sample_paper_data, f"s-{i}") for i in range(4)]
    states = ["saved", "implementing", "shipped", "dismissed"]
    for i, (paper, state) in enumerate(zip(papers, states, strict=False)):
        row = await repo.upsert(
            user_id=created_user.id,
            paper_id=paper.id,
            state=state,
            repo_url="https://github.com/x/y" if state == "shipped" else None,
            dismissal_reason=None,
        )
        # One transaction shares now(); spread the timestamps so the order is testable.
        row.updated_at = datetime(2026, 8, 5, i, tzinfo=UTC)
    await db_session.flush()

    rows = await repo.list_for_user(created_user.id)
    assert [row.state for row, _ in rows] == ["shipped", "implementing", "saved"]
    assert [paper.arxiv_id for _, paper in rows] == ["s-2", "s-1", "s-0"]
    assert rows[0][0].repo_url == "https://github.com/x/y"
