"""LangGraph state and structured output models."""

from typing import List, Optional, TypedDict, Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from src.schemas.conversation import ConversationMessage


# Execution status types
ExecutionStatus = Literal["running", "paused", "completed", "failed"]


class GuardrailScoring(BaseModel):
    """Structured output for guardrail node."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100, description="Relevance score (0-100)")
    reasoning: str = Field(..., description="Brief explanation of the score")
    is_in_scope: bool = Field(..., description="Whether query is in scope for AI/ML research")


class ToolCall(BaseModel):
    """Single tool call specification."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., description="Name of the tool to execute")
    tool_args_json: str = Field(
        default="{}",
        description="JSON-encoded arguments for the tool",
    )


class RouterDecision(BaseModel):
    """Structured output for router node's tool selection."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["execute_tools", "generate"] = Field(
        ..., description="Whether to execute tool(s) or generate a response"
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="Tools to execute (1 or more, run in parallel)",
    )
    reasoning: str = Field(..., description="Brief explanation of the decision")


class ToolExecution(BaseModel):
    """Record of a tool execution."""

    tool_name: str = Field(..., description="Name of the tool that was executed")
    tool_args: dict = Field(default_factory=dict, description="Arguments passed to the tool")
    success: bool = Field(..., description="Whether the execution succeeded")
    result_summary: str = Field(default="", description="Brief summary of the result")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class GradingResult(BaseModel):
    """Structured output for document grading."""

    model_config = ConfigDict(extra="forbid")

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

    # Execution state (for router architecture)
    status: ExecutionStatus
    iteration: int
    max_iterations: int

    # Router decision (LLM's tool selection)
    router_decision: Optional[RouterDecision]

    # Tool execution history
    tool_history: List[ToolExecution]
    last_executed_tools: List[str]  # Tool names from current batch (for routing)

    # Pause/resume support (for future HITL)
    pause_reason: Optional[str]

    # Legacy fields (kept for grading support)
    retrieval_attempts: int

    # Guardrail results
    guardrail_result: Optional[GuardrailScoring]

    # Routing decisions (legacy - kept for backwards compat during migration)
    routing_decision: Optional[str]

    # Retrieved content
    retrieved_chunks: List[dict]
    relevant_chunks: List[dict]

    # Grading results
    grading_results: List[GradingResult]

    # Metadata
    metadata: dict

    # Conversation memory
    conversation_history: List[ConversationMessage]
    session_id: Optional[str]
