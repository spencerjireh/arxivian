"""Papers management router."""

from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from src.schemas.papers import (
    PaperResponse,
    PaperListResponse,
    PaperListItem,
)
from src.dependencies import PaperRepoDep

router = APIRouter()


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    paper_repo: PaperRepoDep,
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
    """Get paginated list of papers from the communal knowledge base."""
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
    )

    paper_items = [PaperListItem.model_validate(p, from_attributes=True) for p in papers]

    return PaperListResponse(total=total, offset=offset, limit=limit, papers=paper_items)


@router.get("/papers/{arxiv_id}", response_model=PaperResponse)
async def get_paper_by_arxiv_id(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
) -> PaperResponse:
    """Get a single paper by arXiv ID."""
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID '{arxiv_id}' not found")
    return PaperResponse.model_validate(paper, from_attributes=True)
