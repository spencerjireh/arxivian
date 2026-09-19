"""Repository for per-user paper lifecycle state (LIFECYCLE-1, SPE-274).

One `user_paper_states` row per `(user, paper)`; `upsert` updates it in place so a state
transition never creates a second row. Flushes only -- the request session owns commit.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.paper import Paper
from src.models.user_paper_state import UserPaperState
from src.utils.logger import get_logger

log = get_logger(__name__)


class UserPaperStateRepository:
    """CRUD over `user_paper_states`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> UserPaperState | None:
        stmt = select(UserPaperState).where(
            UserPaperState.user_id == user_id, UserPaperState.paper_id == paper_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_many(
        self, user_id: uuid.UUID, paper_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, UserPaperState]:
        """Batch fetch keyed by paper id (feed enrichment). Empty input -> no query."""
        if not paper_ids:
            return {}
        stmt = select(UserPaperState).where(
            UserPaperState.user_id == user_id, UserPaperState.paper_id.in_(paper_ids)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.paper_id: row for row in rows}

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        state: str,
        repo_url: str | None,
        dismissal_reason: str | None,
    ) -> UserPaperState:
        """Insert or update the `(user, paper)` row; returns it flushed."""
        existing = await self.get(user_id, paper_id)
        if existing is None:
            row = UserPaperState(
                user_id=user_id,
                paper_id=paper_id,
                state=state,
                repo_url=repo_url,
                dismissal_reason=dismissal_reason,
            )
            self.session.add(row)
        else:
            row = existing
            row.state = state
            row.repo_url = repo_url
            row.dismissal_reason = dismissal_reason
        await self.session.flush()
        log.info(
            "user_paper_state_upserted",
            user_id=str(user_id),
            paper_id=str(paper_id),
            state=state,
            created=existing is None,
        )
        return row

    async def delete(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> bool:
        """Remove the row; True when one existed."""
        stmt = delete(UserPaperState).where(
            UserPaperState.user_id == user_id, UserPaperState.paper_id == paper_id
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0  # type: ignore[possibly-missing-attribute]

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        state: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[UserPaperState, Paper]], int]:
        """The user's rows joined to their papers, newest update first, plus the total."""
        base = select(UserPaperState, Paper).join(Paper, UserPaperState.paper_id == Paper.id)
        base = base.where(UserPaperState.user_id == user_id)
        if state is not None:
            base = base.where(UserPaperState.state == state)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = base.order_by(UserPaperState.updated_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows], int(total)
