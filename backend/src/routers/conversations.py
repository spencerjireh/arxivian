"""Conversations management router for chat history."""

from uuid import UUID

from fastapi import APIRouter, Query

from src.dependencies import ConversationRepoDep, CurrentUserRequired, PaperRepoDep
from src.exceptions import ResourceNotFoundError
from src.schemas.conversations import (
    ConversationDetailResponse,
    ConversationListItem,
    ConversationListResponse,
    ConversationTurnResponse,
    DeleteConversationResponse,
)

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    conversation_repo: ConversationRepoDep,
    paper_repo: PaperRepoDep,
    current_user: CurrentUserRequired,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    arxiv_id: str = Query(..., description="Only threads scoped to this paper"),
) -> ConversationListResponse:
    """List the caller's threads scoped to one paper, most recently updated first.

    Every conversation is paper-scoped (Phase 3), so the paper is required.
    """
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if paper is None:
        raise ResourceNotFoundError("Paper", arxiv_id)
    scope_paper_id = paper.id

    conversations, total = await conversation_repo.get_all(
        offset=offset,
        limit=limit,
        user_id=current_user.id,
        paper_id=scope_paper_id,
    )

    scoped_ids = {conv.paper_id for conv in conversations if isinstance(conv.paper_id, UUID)}
    arxiv_by_paper = {
        paper.id: paper.arxiv_id for paper in await paper_repo.get_by_ids(list(scoped_ids))
    }

    items = []
    for conv in conversations:
        # Get last query from turns if available
        last_query = None
        if conv.turns:
            # Use the first user query as the conversation title
            first_turn = min(conv.turns, key=lambda t: t.turn_number)
            last_query = first_turn.user_query[:100] if first_turn.user_query else None

        items.append(
            ConversationListItem(
                session_id=conv.session_id,
                title=conv.title,
                turn_count=len(conv.turns),
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_query=last_query,
                arxiv_id=arxiv_by_paper.get(conv.paper_id),
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
    paper_repo: PaperRepoDep,
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
    conv = await conversation_repo.get_with_turns(session_id, user_id=current_user.id)
    if not conv:
        raise ResourceNotFoundError("Conversation", session_id)

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
            citations=turn.citations,
            created_at=turn.created_at,
        )
        for turn in sorted(conv.turns, key=lambda t: t.turn_number)
    ]

    scoped_arxiv_id = None
    if isinstance(conv.paper_id, UUID):
        scoped_paper = await paper_repo.get_by_id(str(conv.paper_id))
        scoped_arxiv_id = scoped_paper.arxiv_id if scoped_paper else None

    return ConversationDetailResponse(
        session_id=conv.session_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        arxiv_id=scoped_arxiv_id,
        turns=turns,
    )


@router.delete("/conversations/{session_id}", response_model=DeleteConversationResponse)
async def delete_conversation(
    session_id: str,
    conversation_repo: ConversationRepoDep,
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
    turn_count = await conversation_repo.get_turn_count(session_id, user_id=current_user.id)

    # Check if conversation exists and is owned by user
    conv = await conversation_repo.get_by_session_id(session_id, user_id=current_user.id)
    if not conv:
        raise ResourceNotFoundError("Conversation", session_id)

    # Delete the conversation
    await conversation_repo.delete(session_id, user_id=current_user.id)

    return DeleteConversationResponse(
        session_id=session_id,
        turns_deleted=turn_count,
    )
