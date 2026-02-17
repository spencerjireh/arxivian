"""LangGraph state and structured output models."""

from typing import Any, Required, TypedDict, Annotated, Literal

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
    is_in_scope: bool = Field(..., description="Whether query is in scope for academic research")


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
    error: str | None = Field(default=None, description="Error message if failed")


class GradingResult(BaseModel):
    """Structured output for document grading."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(default="", description="ID of the chunk being graded")
    is_relevant: bool = Field(..., description="Whether chunk is relevant to the query")
    reasoning: str = Field(..., description="Why the chunk is relevant or not (1 sentence)")


class InjectionScan(TypedDict):
    """Result of prompt injection pattern scan."""

    suspicious: bool
    patterns: list[str]


class AgentMetadata(TypedDict, total=False):
    """Typed metadata for agent state."""

    guardrail_threshold: int
    top_k: int
    guardrail_score: int
    injection_scan: InjectionScan
    reasoning_steps: list[str]
    last_guardrail_score: int | None


class ToolOutput(TypedDict, total=False):
    """Output captured from a tool execution for use in generation."""

    tool_name: Required[str]
    data: Required[Any]
    prompt_text: str  # Compact text for generation prompt; falls back to JSON if absent


class AgentState(TypedDict):
    """State passed between LangGraph nodes."""

    # Messages (LangChain message history with reducer)
    messages: Annotated[list[AnyMessage], add_messages]

    # Query tracking
    original_query: str | None
    rewritten_query: str | None

    # Execution state (for router architecture)
    status: ExecutionStatus
    iteration: int
    max_iterations: int

    # Router decision (LLM's tool selection)
    router_decision: RouterDecision | None

    # Tool execution history
    tool_history: list[ToolExecution]
    last_executed_tools: list[str]  # Tool names from current batch (for routing)

    # Pause/resume support (for future HITL)
    pause_reason: str | None

    # Retrieval tracking
    retrieval_attempts: int

    # Guardrail results
    guardrail_result: GuardrailScoring | None

    # Retrieved content
    retrieved_chunks: list[dict]
    relevant_chunks: list[dict]

    # Grading results
    grading_results: list[GradingResult]

    # Tool outputs for generation
    tool_outputs: list[ToolOutput]

    # Metadata
    metadata: AgentMetadata

    # Conversation memory
    conversation_history: list[ConversationMessage]
    session_id: str | None
