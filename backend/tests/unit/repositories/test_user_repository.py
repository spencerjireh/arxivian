"""UserRepository.get_or_create under a first-sign-in race (mocked session)."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.repositories.user_repository import UserRepository


@pytest.mark.unit
class TestGetOrCreateRace:
    async def test_adopts_row_inserted_by_a_parallel_request(self):
        """The lookup misses, the insert collides, the loser rolls back and adopts the row."""
        session = AsyncMock()
        repo = UserRepository(session)
        existing = object()
        repo.get_by_clerk_id = AsyncMock(side_effect=[None, existing])
        repo.update_on_login = AsyncMock()
        collision = IntegrityError("INSERT INTO users", {}, Exception("duplicate key"))

        with patch.object(repo, "create", AsyncMock(side_effect=collision)):
            user, created = await repo.get_or_create(clerk_id="user_1", email="a@b.c")

        assert (user, created) == (existing, False)
        session.rollback.assert_awaited_once()
        assert repo.get_by_clerk_id.await_count == 2
        repo.update_on_login.assert_awaited_once()

    async def test_reraises_when_no_row_exists_after_the_collision(self):
        session = AsyncMock()
        repo = UserRepository(session)
        repo.get_by_clerk_id = AsyncMock(return_value=None)
        collision = IntegrityError("INSERT INTO users", {}, Exception("other constraint"))

        with (
            patch.object(repo, "create", AsyncMock(side_effect=collision)),
            pytest.raises(IntegrityError),
        ):
            await repo.get_or_create(clerk_id="user_1")
        session.rollback.assert_awaited_once()
