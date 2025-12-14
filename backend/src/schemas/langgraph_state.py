"""LangGraph state and structured output models."""

from typing import List, Optional, TypedDict, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GuardrailScoring(BaseModel):
    """Structured output for guardrail node."""

    score: int = Field(..., ge=0, le=100, description="Relevance score (0-100)")
    reasoning: str = Field(..., description="Brief explanation of the score")
    is_in_scope: bool = Field(..., description="Whether query is in scope for AI/ML research")


class GradingResult(BaseModel):
    """Structured output for document grading."""

    chunk_id: str = Field(default="", description="ID of the chunk being graded")
    is_relevant: bool = Field(..., description="Whether chunk is relevant to the query")
    reasoning: str = Field(..., description="Why the chunk is relevant or not (1 sentence)")


class AgentState(TypedDict):
    """State passed between LangGraph nodes."""

    # Messages (LangChain message history with reducer)
    messages: Annotated[List[AnyMessage], add_messages]

    # Query tracking
    original_query: Optional[str]
    rewritten_query: Optional[str]

    # Retrieval tracking
    retrieval_attempts: int

    # Guardrail results
    guardrail_result: Optional[GuardrailScoring]

    # Routing decisions
    routing_decision: Optional[str]

    # Retrieved content
    retrieved_chunks: List[dict]
    relevant_chunks: List[dict]

    # Grading results
    grading_results: List[GradingResult]

    # Metadata
    metadata: dict
