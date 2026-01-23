"""Integration tests for UserRepository."""

import pytest
import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from src.repositories.user_repository import UserRepository


class TestUserRepositoryCreate:
    """Test user creation operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session, sample_user_data):
        """Verify user is created with all fields."""
        repo = UserRepository(session=db_session)

        user = await repo.create(
            clerk_id=sample_user_data["clerk_id"],
            email=sample_user_data["email"],
            first_name=sample_user_data["first_name"],
            last_name=sample_user_data["last_name"],
            profile_image_url=sample_user_data["profile_image_url"],
        )

        assert user.id is not None
        assert user.clerk_id == sample_user_data["clerk_id"]
        assert user.email == sample_user_data["email"]
        assert user.first_name == sample_user_data["first_name"]
        assert user.last_name == sample_user_data["last_name"]
        assert user.profile_image_url == sample_user_data["profile_image_url"]
        assert user.created_at is not None
        assert user.last_login_at is not None

    @pytest.mark.asyncio
    async def test_create_user_minimal(self, db_session):
        """Verify user is created with only required clerk_id."""
        repo = UserRepository(session=db_session)

        clerk_id = f"user_{uuid.uuid4().hex[:16]}"
        user = await repo.create(clerk_id=clerk_id)

        assert user.id is not None
        assert user.clerk_id == clerk_id
        assert user.email is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.profile_image_url is None

    @pytest.mark.asyncio
    async def test_clerk_id_unique_constraint(self, db_session, sample_user_data):
        """Verify uniqueness constraint on clerk_id."""
        repo = UserRepository(session=db_session)

        # Create first user
        await repo.create(clerk_id=sample_user_data["clerk_id"])

        # Attempt to create second user with same clerk_id
        with pytest.raises(IntegrityError):
            await repo.create(clerk_id=sample_user_data["clerk_id"])


class TestUserRepositoryGet:
    """Test user retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_by_clerk_id_found(self, db_session, created_user):
        """Verify user is returned when exists."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_clerk_id(created_user.clerk_id)

        assert retrieved is not None
        assert retrieved.id == created_user.id
        assert retrieved.clerk_id == created_user.clerk_id

    @pytest.mark.asyncio
    async def test_get_by_clerk_id_not_found(self, db_session):
        """Verify None is returned when user doesn't exist."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_clerk_id("nonexistent_clerk_id")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, db_session, created_user):
        """Verify user is returned when email exists."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_email(created_user.email)

        assert retrieved is not None
        assert retrieved.id == created_user.id
        assert retrieved.email == created_user.email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db_session):
        """Verify None is returned when email doesn't exist."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_email("nonexistent@example.com")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, db_session, created_user):
        """Verify user is returned when ID exists."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_id(str(created_user.id))

        assert retrieved is not None
        assert retrieved.id == created_user.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        """Verify None is returned when ID doesn't exist."""
        repo = UserRepository(session=db_session)

        retrieved = await repo.get_by_id(str(uuid.uuid4()))

        assert retrieved is None


class TestUserRepositoryGetOrCreate:
    """Test get_or_create operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, db_session, sample_user_data):
        """Verify new user is created when doesn't exist."""
        repo = UserRepository(session=db_session)

        user, created = await repo.get_or_create(
            clerk_id=sample_user_data["clerk_id"],
            email=sample_user_data["email"],
            first_name=sample_user_data["first_name"],
            last_name=sample_user_data["last_name"],
        )

        assert created is True
        assert user.id is not None
        assert user.clerk_id == sample_user_data["clerk_id"]
        assert user.email == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, db_session, created_user):
        """Verify existing user is returned and last_login is updated."""
        repo = UserRepository(session=db_session)

        original_login = created_user.last_login_at

        user, created = await repo.get_or_create(
            clerk_id=created_user.clerk_id,
            email="new@example.com",  # Different email
        )

        assert created is False
        assert user.id == created_user.id
        # last_login_at should be updated
        assert user.last_login_at >= original_login


class TestUserRepositoryUpdate:
    """Test user update operations."""

    @pytest.mark.asyncio
    async def test_update_on_login_syncs_fields(self, db_session, created_user):
        """Verify profile data is synced from Clerk on login."""
        repo = UserRepository(session=db_session)

        original_login = created_user.last_login_at

        updated_user = await repo.update_on_login(
            created_user,
            email="updated@example.com",
            first_name="Updated",
            last_name="Name",
            profile_image_url="https://example.com/new-avatar.png",
        )

        assert updated_user.email == "updated@example.com"
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.profile_image_url == "https://example.com/new-avatar.png"
        assert updated_user.last_login_at > original_login

    @pytest.mark.asyncio
    async def test_update_on_login_preserves_existing_fields(
        self, db_session, created_user
    ):
        """Verify existing fields are preserved when not provided."""
        repo = UserRepository(session=db_session)

        original_email = created_user.email
        original_first_name = created_user.first_name

        # Only update last_name
        updated_user = await repo.update_on_login(
            created_user,
            last_name="NewLastName",
        )

        assert updated_user.email == original_email
        assert updated_user.first_name == original_first_name
        assert updated_user.last_name == "NewLastName"

    @pytest.mark.asyncio
    async def test_update_last_login_only(self, db_session, created_user):
        """Verify only last_login timestamp is updated."""
        repo = UserRepository(session=db_session)

        original_login = created_user.last_login_at
        original_email = created_user.email

        updated_user = await repo.update_last_login(created_user)

        assert updated_user.last_login_at > original_login
        assert updated_user.email == original_email
