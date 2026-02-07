"""Conversations management router for chat history."""

from fastapi import APIRouter, HTTPException, Query

from src.schemas.conversation import (
    ConversationListItem,
    ConversationListResponse,
    ConversationDetailResponse,
    ConversationTurnResponse,
    DeleteConversationResponse,
    CancelStreamResponse,
)
from src.dependencies import ConversationRepoDep, DbSession, CurrentUserRequired
from src.services.task_registry import task_registry

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    conversation_repo: ConversationRepoDep,
    current_user: CurrentUserRequired,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ConversationListResponse:
    """
    Get paginated list of all conversations.

    Returns conversations ordered by most recently updated first.
    Each item includes a summary with turn count and last query preview.

    Args:
        conversation_repo: Injected conversation repository
        offset: Number of conversations to skip
        limit: Maximum number of conversations to return

    Returns:
        ConversationListResponse with paginated conversations
    """
    conversations, total = await conversation_repo.get_all(
        offset=offset,
        limit=limit,
        user_id=current_user.id,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
    )

    items = []
    for conv in conversations:
        # Get last query from turns if available
        last_query = None
        if conv.turns:
            # Turns are ordered by turn_number, get the last one
            last_turn = max(conv.turns, key=lambda t: t.turn_number)
            last_query = last_turn.user_query[:100] if last_turn.user_query else None

        items.append(
            ConversationListItem(
                session_id=conv.session_id,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
                turn_count=len(conv.turns),
                created_at=conv.created_at,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
                updated_at=conv.updated_at,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
                last_query=last_query,
            )
        )

    return ConversationListResponse(
        total=total,
        offset=offset,
        limit=limit,
        conversations=items,
    )


@router.get("/conversations/{session_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    session_id: str,
    conversation_repo: ConversationRepoDep,
    current_user: CurrentUserRequired,
) -> ConversationDetailResponse:
    """
    Get a conversation with all its turns.

    Args:
        session_id: Session identifier for the conversation
        conversation_repo: Injected conversation repository
        current_user: Authenticated user

    Returns:
        ConversationDetailResponse with full conversation details

    Raises:
        HTTPException: 404 if conversation not found or not owned by user
    """
    conv = await conversation_repo.get_with_turns(session_id, user_id=current_user.id)  # ty: ignore[invalid-argument-type]  # SQLAlchemy
    if not conv:
        raise HTTPException(
            status_code=404, detail=f"Conversation with session_id '{session_id}' not found"
        )

    turns = [
        ConversationTurnResponse(
            turn_number=turn.turn_number,
            user_query=turn.user_query,
            agent_response=turn.agent_response,
            provider=turn.provider,
            model=turn.model,
            guardrail_score=turn.guardrail_score,
            retrieval_attempts=turn.retrieval_attempts,
            rewritten_query=turn.rewritten_query,
            sources=turn.sources,
            reasoning_steps=turn.reasoning_steps,
            created_at=turn.created_at,
        )
        for turn in sorted(conv.turns, key=lambda t: t.turn_number)
    ]

    return ConversationDetailResponse(
        session_id=conv.session_id,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
        created_at=conv.created_at,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
        updated_at=conv.updated_at,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
        turns=turns,
    )


@router.delete("/conversations/{session_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    session_id: str,
    conversation_repo: ConversationRepoDep,
    db: DbSession,
    current_user: CurrentUserRequired,
) -> DeleteConversationResponse:
    """
    Delete a conversation and all its turns.

    This performs a hard delete. Turns are automatically deleted via
    CASCADE foreign key constraint.

    Args:
        session_id: Session identifier for the conversation to delete
        conversation_repo: Injected conversation repository
        db: Database session
        current_user: Authenticated user

    Returns:
        DeleteConversationResponse with deletion summary

    Raises:
        HTTPException: 404 if conversation not found or not owned by user
    """
    # Get turn count before deletion
    turn_count = await conversation_repo.get_turn_count(session_id)

    # Check if conversation exists and is owned by user
    conv = await conversation_repo.get_by_session_id(session_id, user_id=current_user.id)  # ty: ignore[invalid-argument-type]  # SQLAlchemy
    if not conv:
        raise HTTPException(
            status_code=404, detail=f"Conversation with session_id '{session_id}' not found"
        )

    # Delete the conversation
    await conversation_repo.delete(session_id, user_id=current_user.id)  # ty: ignore[invalid-argument-type]  # SQLAlchemy

    return DeleteConversationResponse(
        session_id=session_id,
        turns_deleted=turn_count,
    )


@router.post("/conversations/{session_id}/cancel", response_model=CancelStreamResponse)
async def cancel_stream(
    session_id: str,
    current_user: CurrentUserRequired,
) -> CancelStreamResponse:
    """
    Cancel an active streaming request for a conversation.

    This endpoint allows clients to cancel an in-progress stream for
    a specific session. Useful for implementing a "stop generation"
    button in the frontend.

    Args:
        session_id: Session identifier for the streaming conversation

    Returns:
        CancelStreamResponse indicating whether a stream was cancelled
    """
    cancelled = task_registry.cancel(session_id)

    if cancelled:
        return CancelStreamResponse(
            session_id=session_id,
            cancelled=True,
            message="Stream cancelled successfully",
        )
    else:
        return CancelStreamResponse(
            session_id=session_id,
            cancelled=False,
            message="No active stream found for this session",
        )
