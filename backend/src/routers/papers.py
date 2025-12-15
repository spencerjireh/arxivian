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
from src.dependencies import PaperRepoDep, ChunkRepoDep, DbSession

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
    """
    Get paginated list of papers with optional filters.

    Supports filtering by:
    - Processing status (processed_only)
    - Category (substring match, case-insensitive)
    - Author (substring match, case-insensitive)
    - Publication date range (start_date, end_date)

    Results can be sorted by created_at, published_date, or updated_at.
    List response excludes raw_text for performance.

    Args:
        paper_repo: Injected paper repository
        offset: Number of papers to skip
        limit: Maximum number of papers to return
        processed_only: Filter by pdf_processed status
        category: Filter by category
        author: Filter by author name
        start_date: Filter papers published on or after this date
        end_date: Filter papers published on or before this date
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)

    Returns:
        PaperListResponse with paginated papers
    """
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
async def get_paper_by_arxiv_id(arxiv_id: str, paper_repo: PaperRepoDep) -> PaperResponse:
    """
    Get a single paper by arXiv ID.

    Includes all paper fields including raw_text.

    Args:
        arxiv_id: arXiv ID of the paper
        paper_repo: Injected paper repository

    Returns:
        PaperResponse with full paper details

    Raises:
        HTTPException: 404 if paper not found
    """
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID '{arxiv_id}' not found")
    return PaperResponse.model_validate(paper, from_attributes=True)


@router.delete("/papers/{arxiv_id}", response_model=DeletePaperResponse)
async def delete_paper(
    arxiv_id: str,
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    db: DbSession,
) -> DeletePaperResponse:
    """
    Delete a paper and all its associated chunks by arXiv ID.

    This performs a hard delete. Chunks are automatically deleted via
    CASCADE foreign key constraint.

    Args:
        arxiv_id: arXiv ID of the paper to delete
        paper_repo: Injected paper repository
        chunk_repo: Injected chunk repository
        db: Database session

    Returns:
        DeletePaperResponse with deletion summary

    Raises:
        HTTPException: 404 if paper not found
    """
    paper = await paper_repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with arXiv ID '{arxiv_id}' not found")

    chunk_count = await chunk_repo.count_by_paper_id(str(paper.id))
    title = paper.title

    await paper_repo.delete_by_arxiv_id(arxiv_id)
    await db.commit()

    return DeletePaperResponse(
        arxiv_id=arxiv_id,
        title=title,
        chunks_deleted=chunk_count,
    )
