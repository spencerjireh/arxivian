"""Integration tests for UserPaperStateRepository (real test DB)."""

from __future__ import annotations

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

    rows, total = await repo.list_for_user(created_user.id)
    assert total == 1 and rows[0][0].state == "dismissed" and rows[0][1].arxiv_id == "s-1"


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
async def test_list_for_user_filters_and_paginates(db_session, sample_paper_data, created_user):
    repo = UserPaperStateRepository(db_session)
    papers = [await _paper(db_session, sample_paper_data, f"s-{i}") for i in range(4)]
    states = ["saved", "saved", "shipped", "dismissed"]
    for paper, state in zip(papers, states):
        await repo.upsert(
            user_id=created_user.id,
            paper_id=paper.id,
            state=state,
            repo_url="https://github.com/x/y" if state == "shipped" else None,
            dismissal_reason=None,
        )

    saved, total = await repo.list_for_user(created_user.id, state="saved")
    assert total == 2 and {row.state for row, _ in saved} == {"saved"}

    page, total = await repo.list_for_user(created_user.id, offset=1, limit=2)
    assert total == 4 and len(page) == 2

    shipped, _ = await repo.list_for_user(created_user.id, state="shipped")
    assert shipped[0][0].repo_url == "https://github.com/x/y"
