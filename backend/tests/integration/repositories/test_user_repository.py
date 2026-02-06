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


class TestUserRepositoryPreferences:
    """Test user preferences operations."""

    @pytest.mark.asyncio
    async def test_update_preferences_stores_jsonb(self, db_session, created_user):
        """Verify preferences are stored as JSONB."""
        repo = UserRepository(session=db_session)

        preferences = {
            "arxiv_searches": [
                {
                    "name": "ML Papers",
                    "query": "machine learning",
                    "categories": ["cs.LG"],
                    "max_results": 10,
                    "enabled": True,
                }
            ],
            "notification_settings": {"email_digest": True},
        }

        updated_user = await repo.update_preferences(created_user, preferences)

        assert updated_user.preferences is not None
        assert updated_user.preferences["arxiv_searches"][0]["name"] == "ML Papers"
        assert updated_user.preferences["arxiv_searches"][0]["query"] == "machine learning"
        assert updated_user.preferences["notification_settings"]["email_digest"] is True

    @pytest.mark.asyncio
    async def test_update_preferences_updates_timestamp(self, db_session, created_user):
        """Verify updated_at timestamp is changed."""
        repo = UserRepository(session=db_session)

        original_updated_at = created_user.updated_at

        await repo.update_preferences(created_user, {"test": "value"})

        assert created_user.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_update_preferences_replaces_existing(self, db_session, created_user):
        """Verify preferences replace existing values completely."""
        repo = UserRepository(session=db_session)

        # Set initial preferences
        await repo.update_preferences(created_user, {"key1": "value1", "key2": "value2"})

        # Replace with new preferences
        updated_user = await repo.update_preferences(created_user, {"key3": "value3"})

        assert "key1" not in updated_user.preferences
        assert "key2" not in updated_user.preferences
        assert updated_user.preferences["key3"] == "value3"

    @pytest.mark.asyncio
    async def test_get_users_with_searches_returns_matching_users(self, db_session):
        """Verify users with arxiv_searches are returned."""
        repo = UserRepository(session=db_session)

        # Create user with searches
        user_with_searches = await repo.create(
            clerk_id=f"user_{uuid.uuid4().hex[:16]}",
            email=f"with-searches-{uuid.uuid4().hex[:8]}@example.com",
        )
        await repo.update_preferences(
            user_with_searches,
            {
                "arxiv_searches": [
                    {"name": "Test", "query": "test", "enabled": True}
                ]
            },
        )

        # Create user without searches
        user_without_searches = await repo.create(
            clerk_id=f"user_{uuid.uuid4().hex[:16]}",
            email=f"no-searches-{uuid.uuid4().hex[:8]}@example.com",
        )
        await repo.update_preferences(
            user_without_searches,
            {"notification_settings": {"email_digest": False}},
        )

        users = await repo.get_users_with_searches()

        user_ids = [u.id for u in users]
        assert user_with_searches.id in user_ids
        assert user_without_searches.id not in user_ids

    @pytest.mark.asyncio
    async def test_get_users_with_searches_excludes_empty_searches(self, db_session):
        """Verify users with empty arxiv_searches list are excluded."""
        repo = UserRepository(session=db_session)

        # Create user with empty searches list
        user = await repo.create(
            clerk_id=f"user_{uuid.uuid4().hex[:16]}",
            email=f"empty-{uuid.uuid4().hex[:8]}@example.com",
        )
        await repo.update_preferences(user, {"arxiv_searches": []})

        users = await repo.get_users_with_searches()

        user_ids = [u.id for u in users]
        assert user.id not in user_ids

    @pytest.mark.asyncio
    async def test_get_users_with_searches_excludes_null_preferences(self, db_session):
        """Verify users with null preferences are excluded."""
        repo = UserRepository(session=db_session)

        # Create user with no preferences
        user = await repo.create(
            clerk_id=f"user_{uuid.uuid4().hex[:16]}",
            email=f"null-{uuid.uuid4().hex[:8]}@example.com",
        )
        # Don't set any preferences

        users = await repo.get_users_with_searches()

        user_ids = [u.id for u in users]
        assert user.id not in user_ids

    @pytest.mark.asyncio
    async def test_get_users_with_searches_handles_multiple_users(self, db_session):
        """Verify multiple users with searches are all returned."""
        repo = UserRepository(session=db_session)

        # Create multiple users with searches
        users_created = []
        for i in range(3):
            user = await repo.create(
                clerk_id=f"user_{uuid.uuid4().hex[:16]}",
                email=f"multi-{i}-{uuid.uuid4().hex[:8]}@example.com",
            )
            await repo.update_preferences(
                user,
                {
                    "arxiv_searches": [
                        {"name": f"Search {i}", "query": f"query {i}", "enabled": True}
                    ]
                },
            )
            users_created.append(user)

        users = await repo.get_users_with_searches()

        user_ids = [u.id for u in users]
        for created in users_created:
            assert created.id in user_ids
