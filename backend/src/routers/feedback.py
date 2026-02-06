"""Feedback collection endpoint for Langfuse."""

from fastapi import APIRouter

from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.dependencies import CurrentUserRequired
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: CurrentUserRequired,
) -> FeedbackResponse:
    """Submit user feedback for a trace."""
    try:
        from src.clients.traced_llm_client import _get_langfuse
    except ImportError:
        return FeedbackResponse(success=False, message="Langfuse not installed")

    langfuse = _get_langfuse()
    if not langfuse:
        return FeedbackResponse(success=False, message="Langfuse not enabled")

    try:
        langfuse.score(
            trace_id=request.trace_id,
            name="user-feedback",
            value=request.score,
            comment=request.comment,
        )
        return FeedbackResponse(success=True)
    except Exception as e:
        log.error("feedback_submission_failed", error=str(e), trace_id=request.trace_id)
        return FeedbackResponse(success=False, message="Failed to submit feedback")
