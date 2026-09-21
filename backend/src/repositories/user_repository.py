"""Repository for User model operations."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.utils.logger import get_logger

log = get_logger(__name__)


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by UUID."""
        log.debug("query user by id", user_id=user_id)
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        log.debug("query result", found=user is not None)
        return user

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        """Get user by Clerk ID."""
        log.debug("query user by clerk_id", clerk_id=clerk_id)
        result = await self.session.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        log.debug("query result", found=user is not None)
        return user

    async def create(
        self,
        clerk_id: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        profile_image_url: str | None = None,
    ) -> User:
        """
        Create a new user.

        Caller is responsible for committing the transaction.
        """
        user = User(
            clerk_id=clerk_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_image_url=profile_image_url,
            last_login_at=datetime.now(UTC),
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        log.info("user created", clerk_id=clerk_id, email=email)
        return user

    async def get_or_create(
        self,
        clerk_id: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        profile_image_url: str | None = None,
    ) -> tuple[User, bool]:
        """
        Get existing user or create a new one.

        This handles the common pattern of syncing user on first auth.

        Args:
            clerk_id: Clerk user ID
            email: User email
            first_name: User first name
            last_name: User last name
            profile_image_url: URL to user's profile image

        Returns:
            Tuple of (user, created) where created is True if user was newly created
        """
        user = await self.get_by_clerk_id(clerk_id)
        if user:
            # Update last login and any changed profile info
            await self.update_on_login(
                user,
                email=email,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
            )
            return user, False

        # First sign-in fires several requests at once and each one runs this dependency,
        # so a parallel request may insert the row between the lookup and this insert.
        # This runs before any other work in the request, so rolling back only discards
        # the failed insert; the loser then adopts the row.
        try:
            user = await self.create(
                clerk_id=clerk_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
            )
        except IntegrityError:
            await self.session.rollback()
            user = await self.get_by_clerk_id(clerk_id)
            if user is None:
                raise
            log.info("user create raced, adopted existing row", clerk_id=clerk_id)
            await self.update_on_login(
                user,
                email=email,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
            )
            return user, False
        return user, True

    async def update_on_login(
        self,
        user: User,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        profile_image_url: str | None = None,
    ) -> User:
        """
        Update user's last login time and sync profile data from Clerk.

        Caller is responsible for committing the transaction.
        """
        update_data = {
            "last_login_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Only update fields if they have values (to preserve existing data)
        if email is not None:
            update_data["email"] = email
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if profile_image_url is not None:
            update_data["profile_image_url"] = profile_image_url

        await self.session.execute(update(User).where(User.id == user.id).values(**update_data))
        await self.session.flush()

        # Refresh to get updated values
        await self.session.refresh(user)
        log.debug("user login updated", clerk_id=user.clerk_id)
        return user

    async def update_tier(self, user: User, tier: str) -> User:
        """
        Update user's tier.

        Caller is responsible for committing the transaction.

        Args:
            user: The user to update
            tier: New tier value

        Returns:
            Updated user
        """
        now = datetime.now(UTC)
        await self.session.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                tier=tier,
                updated_at=now,
            )
        )
        await self.session.flush()
        await self.session.refresh(user)
        log.debug("user tier updated", clerk_id=user.clerk_id, tier=tier)
        return user

    async def update_preferences(self, user: User, preferences: dict) -> User:
        """
        Update user's preferences.

        Caller is responsible for committing the transaction.

        Args:
            user: The user to update
            preferences: New preferences dict to set

        Returns:
            Updated user
        """
        now = datetime.now(UTC)
        await self.session.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                preferences=preferences,
                updated_at=now,
            )
        )
        await self.session.flush()
        await self.session.refresh(user)
        log.debug("user preferences updated", clerk_id=user.clerk_id)
        return user
