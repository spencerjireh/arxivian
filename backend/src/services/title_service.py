"""Conversation title generation service."""

from __future__ import annotations

from src.clients.base_llm_client import BaseLLMClient
from src.services.agent_service.prompts import TITLE_SYSTEM_PROMPT
from src.utils.logger import get_logger

log = get_logger(__name__)


async def generate_title(llm_client: BaseLLMClient, query: str) -> str | None:
    """Generate a short descriptive title for a conversation.

    Uses gpt-4o-mini to produce a 4-8 word title from the first user query.
    Returns None on any failure so callers can fall back gracefully.
    """
    try:
        raw = await llm_client.generate_completion(
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            model="openai/gpt-4o-mini",
            temperature=0.3,
            max_tokens=30,
        )
        title = raw.strip().strip('"').strip("'").strip()
        return title[:200] if title else None
    except Exception:
        log.warning("title_generation_failed", query=query[:100], exc_info=True)
        return None
