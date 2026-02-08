"""Papers management router."""

from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from src.schemas.papers import (
    PaperResponse,
    PaperListResponse,
    PaperListItem,
    DeletePaperResponse,
)
from src.dependencies import (
    PaperRepoDep,
    ChunkRepoDep,
    DbSession,
    CurrentUserOptional,
    CurrentUserRequired,
)

router = APIRouter()


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    paper_repo: PaperRepoDep,
    current_user: CurrentUserOptional,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    processed_only: Optional[bool] = None,
    category: Optional[str] = None,
    author: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Literal["created_at", "published_date", "updated_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> PaperListResponse:
    """Get paginated list of papers. Anonymous sees system papers only."""
    user_id = current_user.id if current_user else None
    papers, total = await paper_repo.get_all(
        offset=offset,
        limit=limit,
        processed_only=processed_only,
        category_filter=category,
        author_filter=author,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        user_id=user_id,
    )

    paper_items = [PaperListItem.model_validate(p, from_attributes=True) for p in papers]

    return PaperListResponse(total=total, offset=offset, limit=limit, papers=paper_items)


@router.get("/papers/{arxiv_id}", response_model=PaperResponse)
async def get_paper_by_arxiv_id(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    current_user: CurrentUserOptional,
) -> PaperResponse:
    """Get a single paper by arXiv ID. Scoped to user + system ownership."""
    user_id = current_user.id if current_user else None
    paper = await paper_repo.get_by_arxiv_id(arxiv_id, user_id=user_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID '{arxiv_id}' not found")
    return PaperResponse.model_validate(paper, from_attributes=True)


@router.delete("/papers/{arxiv_id}", response_model=DeletePaperResponse)
async def delete_paper(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    db: DbSession,
    current_user: CurrentUserRequired,
) -> DeletePaperResponse:
    """Delete a paper and its chunks. Requires authentication."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id, user_id=current_user.id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID '{arxiv_id}' not found")

    chunk_count = await chunk_repo.count_by_paper_id(str(paper.id))
    title = paper.title

    await paper_repo.delete_by_arxiv_id(arxiv_id, user_id=current_user.id)
    await db.commit()

    return DeletePaperResponse(
        arxiv_id=arxiv_id,
        title=title,  # ty: ignore[invalid-argument-type]  # SQLAlchemy
        chunks_deleted=chunk_count,
    )
