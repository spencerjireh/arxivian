"""Per-user paper lifecycle state (LIFECYCLE-1): save / dismiss / implementing / shipped."""

from fastapi import APIRouter, Response, status

from src.dependencies import (
    CurrentUserRequired,
    FeedServiceDep,
    PaperRepoDep,
    UserPaperStateRepoDep,
)
from src.exceptions import ResourceNotFoundError
from src.schemas.feed import LibraryResponse
from src.schemas.paper_states import UserPaperStateRequest, UserPaperStateResponse

router = APIRouter()


@router.put("/papers/{arxiv_id}/state", response_model=UserPaperStateResponse)
async def put_paper_state(
    arxiv_id: str,
    body: UserPaperStateRequest,
    user: CurrentUserRequired,
    paper_repo: PaperRepoDep,
    state_repo: UserPaperStateRepoDep,
) -> UserPaperStateResponse:
    """Set the caller's lifecycle state for a paper (upsert; one row per user + paper)."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if paper is None:
        raise ResourceNotFoundError("Paper", arxiv_id)
    row = await state_repo.upsert(
        user_id=user.id,
        paper_id=paper.id,
        state=body.state,
        repo_url=str(body.repo_url) if body.repo_url is not None else None,
        dismissal_reason=body.dismissal_reason,
    )
    return UserPaperStateResponse.model_validate(row)


@router.delete("/papers/{arxiv_id}/state", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper_state(
    arxiv_id: str,
    user: CurrentUserRequired,
    paper_repo: PaperRepoDep,
    state_repo: UserPaperStateRepoDep,
) -> Response:
    """Clear the caller's lifecycle state for a paper."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if paper is None:
        raise ResourceNotFoundError("Paper", arxiv_id)
    deleted = await state_repo.delete(user.id, paper.id)
    if not deleted:
        raise ResourceNotFoundError("Paper state", arxiv_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me/library", response_model=LibraryResponse)
async def get_library(user: CurrentUserRequired, feed_service: FeedServiceDep) -> LibraryResponse:
    """The caller's papers grouped by lifecycle state, as feed cards (SPE-296)."""
    return await feed_service.get_library(user)
