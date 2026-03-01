"""Clerk webhook endpoint for user lifecycle events."""

from fastapi import APIRouter, Request
from sqlalchemy import delete

from src.config import get_settings
from src.database import AsyncSessionLocal
from src.exceptions import ValidationError
from src.models.conversation import Conversation
from src.models.task_execution import TaskExecution
from src.models.usage_counter import UsageCounter
from src.repositories.user_repository import UserRepository
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_svix_signature(payload: bytes, headers: dict[str, str], secret: str) -> dict:
    """Verify Svix webhook signature and return parsed payload.

    Raises ValidationError if the secret is unconfigured or the signature is invalid.
    """
    if not secret:
        raise ValidationError("Webhook secret not configured")

    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        wh = Webhook(secret)
        return wh.verify(payload, headers)
    except WebhookVerificationError as exc:
        log.warning("webhook signature verification failed", error=str(exc))
        raise ValidationError("Invalid webhook signature")


@router.post("/clerk")
async def clerk_webhook(request: Request) -> dict:
    """Handle Clerk webhook events (user.updated, user.deleted).

    Authenticates via Svix signature verification, not Clerk JWT.
    """
    settings = get_settings()
    body = await request.body()
    svix_headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    event = _verify_svix_signature(body, svix_headers, settings.clerk_webhook_secret)

    event_type = event.get("type", "")
    data = event.get("data", {})
    clerk_id = data.get("id", "")

    if not clerk_id:
        log.warning("webhook missing clerk user id", event_type=event_type)
        return {"status": "ignored"}

    if event_type == "user.updated":
        await _handle_user_updated(clerk_id, data)
    elif event_type == "user.deleted":
        await _handle_user_deleted(clerk_id)
    else:
        log.debug("webhook event ignored", event_type=event_type)

    return {"status": "ok"}


async def _handle_user_updated(clerk_id: str, data: dict) -> None:
    """Sync updated profile data from Clerk."""
    email = _extract_primary_email(data)
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    profile_image_url = data.get("image_url") or data.get("profile_image_url")

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_clerk_id(clerk_id)
        if not user:
            log.info("webhook user.updated for unknown user, skipping", clerk_id=clerk_id)
            return

        await repo.update_on_login(
            user,
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_image_url=profile_image_url,
        )
        await session.commit()
        log.info("webhook user.updated synced", clerk_id=clerk_id)


async def _handle_user_deleted(clerk_id: str) -> None:
    """Delete user and all owned records."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_clerk_id(clerk_id)
        if not user:
            log.info("webhook user.deleted for unknown user, skipping", clerk_id=clerk_id)
            return

        user_id = user.id

        # Delete records with non-nullable user_id FKs first
        await session.execute(delete(TaskExecution).where(TaskExecution.user_id == user_id))
        await session.execute(delete(UsageCounter).where(UsageCounter.user_id == user_id))

        # Delete conversations (turns auto-cascade via relationship)
        await session.execute(delete(Conversation).where(Conversation.user_id == user_id))

        # Nullify paper.ingested_by (nullable FK -- keep paper data)
        from sqlalchemy import update as sa_update
        from src.models.paper import Paper

        await session.execute(
            sa_update(Paper).where(Paper.ingested_by == user_id).values(ingested_by=None)
        )

        # Delete user
        await session.delete(user)
        await session.commit()
        log.info("webhook user.deleted completed", clerk_id=clerk_id, user_id=str(user_id))


def _extract_primary_email(data: dict) -> str | None:
    """Extract primary email from Clerk webhook data."""
    email_addresses = data.get("email_addresses", [])
    primary_email_id = data.get("primary_email_address_id")

    for addr in email_addresses:
        if addr.get("id") == primary_email_id:
            return addr.get("email_address")

    # Fallback: use first email if available
    if email_addresses:
        return email_addresses[0].get("email_address")

    return None
