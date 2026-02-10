"""Multi-turn conversation persistence tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.stream import MetadataEventData
from src.services.agent_service import AgentService

from .helpers import consume_stream
from .scenarios import MULTI_TURN_SCENARIOS


@pytest.mark.inteval
@pytest.mark.parametrize(
    "scenario",
    MULTI_TURN_SCENARIOS,
    ids=[s.id for s in MULTI_TURN_SCENARIOS],
)
async def test_multi_turn_persistence(
    agent_service: AgentService,
    db_session: AsyncSession,
    seed_user: User,
    scenario,
):
    """Sequential turns via ask_stream() with same session_id are persisted."""
    session_id: str | None = None

    for i, query in enumerate(scenario.turns):
        result = await consume_stream(agent_service, query, session_id=session_id)

        assert result.done_event is not None, f"Turn {i} should complete with DONE"
        assert result.metadata_event is not None, f"Turn {i} should have METADATA"
        assert len(result.answer) > 10, f"Turn {i} answer too short"

        # Capture session_id from first turn
        if session_id is None:
            session_id = result.session_id
            assert session_id is not None, "First turn should generate session_id"

    # Verify conversation + turns in DB
    conv_repo = ConversationRepository(db_session)
    conversation = await conv_repo.get_with_turns(session_id, user_id=seed_user.id)

    assert conversation is not None, f"Conversation {session_id} not found in DB"
    assert len(conversation.turns) == len(scenario.turns), (
        f"Expected {len(scenario.turns)} turns, got {len(conversation.turns)}"
    )

    # Verify turn content
    for i, turn in enumerate(sorted(conversation.turns, key=lambda t: t.turn_number)):
        assert turn.user_query == scenario.turns[i], (
            f"Turn {i} query mismatch: {turn.user_query}"
        )
        assert len(turn.agent_response) > 0, f"Turn {i} should have a response"


@pytest.mark.inteval
async def test_session_id_preserved_across_turns(
    agent_service: AgentService,
    db_session: AsyncSession,
    seed_user: User,
):
    """Verify turn_number increments and session_id is stable across turns."""
    queries = [
        "What is the BERT model?",
        "How is it different from GPT-3?",
    ]

    session_id: str | None = None
    turn_numbers: list[int] = []

    for query in queries:
        result = await consume_stream(agent_service, query, session_id=session_id)
        assert result.metadata_event is not None

        meta = result.metadata_event.data
        assert isinstance(meta, MetadataEventData)

        if session_id is None:
            session_id = meta.session_id
        else:
            assert meta.session_id == session_id, "session_id should be stable"

        turn_numbers.append(meta.turn_number)

    # Turn numbers should increment
    assert turn_numbers[0] < turn_numbers[1], (
        f"Turn numbers should increment: {turn_numbers}"
    )

    # Verify in DB
    conv_repo = ConversationRepository(db_session)
    conversation = await conv_repo.get_with_turns(session_id, user_id=seed_user.id)
    assert conversation is not None
    assert len(conversation.turns) == 2
