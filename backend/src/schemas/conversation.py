"""Conversation schemas for multi-turn memory."""

from dataclasses import dataclass
from typing import Literal, TypedDict


class ConversationMessage(TypedDict):
    """A single message in a conversation."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class TurnData:
    """Data for saving a conversation turn."""

    user_query: str
    agent_response: str
    provider: str
    model: str
    guardrail_score: int | None = None
    retrieval_attempts: int = 1
    rewritten_query: str | None = None
    sources: list[dict] | None = None
    reasoning_steps: list[str] | None = None
