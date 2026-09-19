"""Per-user paper lifecycle state (LIFECYCLE-1): save / dismiss / implementing / shipped."""

from fastapi import APIRouter, Query, Response, status

from src.dependencies import CurrentUserRequired, PaperRepoDep, UserPaperStateRepoDep
from src.exceptions import ResourceNotFoundError
from src.schemas.feed import (
    FeedPaper,
    PaperState,
    UserPaperListItem,
    UserPaperListResponse,
    UserPaperStateRequest,
    UserPaperStateResponse,
)

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


@router.get("/users/me/papers", response_model=UserPaperListResponse)
async def list_my_papers(
    user: CurrentUserRequired,
    state_repo: UserPaperStateRepoDep,
    state: PaperState | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> UserPaperListResponse:
    """The caller's papers by lifecycle state, newest update first (library read)."""
    rows, total = await state_repo.list_for_user(user.id, state=state, offset=offset, limit=limit)
    return UserPaperListResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[
            UserPaperListItem(
                paper=FeedPaper.model_validate(paper),
                state=UserPaperStateResponse.model_validate(row),
            )
            for row, paper in rows
        ],
    )
