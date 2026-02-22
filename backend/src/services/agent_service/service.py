"""Agent service with LangGraph workflow."""

from __future__ import annotations

import time
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, AsyncIterator
from uuid import UUID

if TYPE_CHECKING:
    from src.repositories.usage_counter_repository import UsageCounterRepository

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from redis.asyncio import Redis

from src.clients.base_llm_client import BaseLLMClient
from src.clients.langfuse_utils import set_trace_context
from src.config import get_settings

try:
    from langfuse.callback import CallbackHandler

    LANGFUSE_CALLBACK_AVAILABLE = True
except ImportError:
    LANGFUSE_CALLBACK_AVAILABLE = False
from src.clients.arxiv_client import ArxivClient
from src.services.search_service import SearchService
from src.services.ingest_service import IngestService
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.paper_repository import PaperRepository
from src.schemas.conversation import ConversationMessage, ThinkingStepDict, TurnData
from src.schemas.stream import (
    StreamEvent,
    StreamEventType,
    StatusEventData,
    ContentEventData,
    SourcesEventData,
    MetadataEventData,
    ErrorEventData,
    CitationsEventData,
    DoneEventData,
    ConfirmIngestEventData,
    IngestCompleteEventData,
)
from src.schemas.common import SourceInfo
from src.utils.logger import get_logger
from .context import AgentContext

log = get_logger(__name__)

# Sentinel strings in LangGraph errors indicating a missing/expired checkpoint.
# Centralized here so there is exactly one place to update if upstream messages change.
_CHECKPOINT_ERROR_PATTERNS = ("no checkpoint found", "missing thread_id")

# Map LangGraph node names to user-friendly step names
NODE_TO_STEP = {
    "classify_and_route": "classifying",
    "out_of_scope": "out_of_scope",
    "executor": "executing",
    "evaluate_batch": "evaluating",
    "generate": "generation",
    "confirm_ingest": "confirming",
}

NODE_MESSAGES = {
    "classify_and_route": "Classifying query...",
    "out_of_scope": "Generating out-of-scope response...",
    "evaluate_batch": "Evaluating retrieval quality...",
    "generate": "Generating answer...",
    "confirm_ingest": "Waiting for confirmation...",
}

# Nodes whose start event is synthesized from custom events instead
_SKIP_START_STATUS = {"executor"}


class _StepTracker:
    """Tracks start/end times for workflow steps to build ThinkingStepDicts."""

    def __init__(self) -> None:
        self.steps: list[ThinkingStepDict] = []
        self._starts: dict[str, float] = {}

    @staticmethod
    def _key(step: str, details: dict | None) -> str:
        if step == "executing" and details and details.get("tool_name"):
            return f"executing:{details['tool_name']}"
        return step

    def start(self, step: str, details: dict | None = None) -> None:
        """Record the start time for a workflow step."""
        self._starts[self._key(step, details)] = time.time()

    def end(self, step: str, message: str, details: dict | None) -> None:
        """Record completion of a workflow step, pairing with its start time."""
        key = self._key(step, details)
        started = self._starts.pop(key, None)
        if started is None:
            return
        now = time.time()
        self.steps.append(
            {
                "step": step,
                "message": message,
                "details": details,
                "tool_name": (details or {}).get("tool_name"),
                "started_at": datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
                "completed_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            }
        )


class AgentService:
    """
    Service for executing agent workflows.

    Wraps LangGraph workflow with streaming SSE events.
    Uses router-based architecture for dynamic tool selection.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        graph: CompiledStateGraph,
        redis: Redis | None = None,
        ingest_service: IngestService | None = None,
        arxiv_client: ArxivClient | None = None,
        paper_repository: PaperRepository | None = None,
        conversation_repo: ConversationRepository | None = None,
        conversation_window: int = 5,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        min_score: float = 0.5,
        max_retrieval_attempts: int = 3,
        max_iterations: int = 5,
        temperature: float = 0.3,
        user_id: UUID | None = None,
        daily_ingests: int | None = None,
        usage_counter_repo: UsageCounterRepository | None = None,
    ):
        self.graph = graph
        self.redis = redis
        self.ingest_service = ingest_service
        self.usage_counter_repo = usage_counter_repo
        self.context = AgentContext(
            llm_client=llm_client,
            search_service=search_service,
            ingest_service=ingest_service,
            arxiv_client=arxiv_client,
            paper_repository=paper_repository,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
            min_score=min_score,
            max_retrieval_attempts=max_retrieval_attempts,
            max_iterations=max_iterations,
            temperature=temperature,
            user_id=user_id,
            daily_ingests=daily_ingests,
            usage_counter_repo=usage_counter_repo,
        )
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Stream consumption: translates LangGraph astream events to SSE
    # ------------------------------------------------------------------

    async def _consume_stream(
        self,
        input_data: dict | Command,
        config: dict,
        final_state: dict,
        tracker: _StepTracker,
        sources_emitted: bool = False,
    ) -> AsyncIterator[StreamEvent | dict]:
        """
        Consume graph.astream and yield StreamEvent objects.

        Yields a ``{"__interrupt__": data}`` sentinel dict if the graph is
        interrupted (HITL). The caller is responsible for handling it.
        """
        seen_nodes: set[str] = set()
        content_tokens_emitted = 0

        async for stream_mode, chunk in self.graph.astream(
            input_data,
            config,
            stream_mode=["updates", "custom"],
        ):
            if stream_mode == "custom":
                # Custom events from get_stream_writer()
                if not isinstance(chunk, dict):
                    continue
                event_type = chunk.get("type")

                if event_type == "token":
                    token = chunk.get("token", "")
                    if token:
                        content_tokens_emitted += 1
                        yield StreamEvent(
                            event=StreamEventType.CONTENT,
                            data=ContentEventData(token=token),
                        )

                elif event_type == "tool_start":
                    tool_name = chunk.get("tool_name", "")
                    tool_details = {"tool_name": tool_name}
                    tool_msg = f"Calling {tool_name}..."
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="executing",
                            message=tool_msg,
                            details=tool_details,
                        ),
                    )
                    tracker.start("executing", tool_details)

                elif event_type == "tool_end":
                    tool_name = chunk.get("tool_name", "")
                    success = chunk.get("success", True)
                    status = "completed" if success else "failed"
                    tool_end_msg = f"{tool_name} {status}"
                    tool_details = {"tool_name": tool_name, "success": success}
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="executing",
                            message=tool_end_msg,
                            details=tool_details,
                        ),
                    )
                    tracker.end("executing", tool_end_msg, tool_details)

                elif event_type == "citations_data":
                    citations = chunk.get("data", {})
                    yield StreamEvent(
                        event=StreamEventType.CITATIONS,
                        data=CitationsEventData(**citations),
                    )

            elif stream_mode == "updates":
                if not isinstance(chunk, dict):
                    continue

                # Check for interrupt
                if "__interrupt__" in chunk:
                    yield {"__interrupt__": chunk["__interrupt__"]}
                    continue

                # Process node updates
                for node_name, output in chunk.items():
                    if node_name not in NODE_TO_STEP:
                        continue

                    step = NODE_TO_STEP[node_name]

                    # Emit start status for nodes we haven't seen yet
                    if node_name not in seen_nodes and node_name not in _SKIP_START_STATUS:
                        message = NODE_MESSAGES.get(node_name, f"Processing {node_name}...")
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(step=step, message=message),
                        )
                        tracker.start(step)
                        seen_nodes.add(node_name)

                    # Update final_state with latest output
                    if isinstance(output, dict):
                        final_state.update(output)

                    # Emit detailed status per node
                    if node_name == "classify_and_route" and output.get(
                        "classification_result"
                    ):
                        result = output["classification_result"]
                        classify_details = {
                            "score": result.scope_score,
                            "intent": result.intent,
                            "threshold": self.context.guardrail_threshold,
                            "reasoning": result.reasoning,
                        }
                        classify_msg = (
                            f"Classified: intent={result.intent}, "
                            f"score={result.scope_score}"
                        )
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="classifying",
                                message=classify_msg,
                                details=classify_details,
                            ),
                        )
                        tracker.end("classifying", classify_msg, classify_details)

                    elif node_name == "out_of_scope":
                        tracker.end("out_of_scope", "Out of scope", None)

                    elif node_name == "generate":
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="generation",
                                message="Generation complete",
                            ),
                        )
                        tracker.end("generation", "Generation complete", None)

                    elif node_name == "confirm_ingest":
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="confirming",
                                message="Confirmation received",
                            ),
                        )
                        tracker.end("confirming", "Confirmation received", None)

                    elif node_name == "evaluate_batch":
                        eval_result = output.get("evaluation_result")
                        relevant = output.get("relevant_chunks", [])
                        total_chunks = len(final_state.get("retrieved_chunks", []))
                        eval_details = {
                            "sufficient": eval_result.sufficient if eval_result else None,
                            "total": total_chunks,
                            "reasoning": eval_result.reasoning if eval_result else "",
                        }
                        eval_msg = (
                            f"Evaluation: "
                            f"{'sufficient' if eval_result and eval_result.sufficient else 'insufficient'}"
                        )
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="evaluating",
                                message=eval_msg,
                                details=eval_details,
                            ),
                        )
                        tracker.end("evaluating", eval_msg, eval_details)

                        # Emit sources after evaluation (before generation)
                        if not sources_emitted and relevant:
                            sources = [
                                SourceInfo(
                                    arxiv_id=c["arxiv_id"],
                                    title=c["title"],
                                    authors=c.get("authors", []),
                                    pdf_url=c.get(
                                        "pdf_url",
                                        f"https://arxiv.org/pdf/{c['arxiv_id']}.pdf",
                                    ),
                                    relevance_score=c.get("score", 0.0),
                                    published_date=c.get("published_date"),
                                    was_graded_relevant=True,
                                )
                                for c in relevant[: self.context.top_k]
                            ]
                            yield StreamEvent(
                                event=StreamEventType.SOURCES,
                                data=SourcesEventData(sources=sources),
                            )
                            sources_emitted = True

        # Fallback: emit answer as single CONTENT event if no tokens streamed
        if content_tokens_emitted == 0 and final_state.get("messages"):
            last_msg = final_state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                content = last_msg.content
                answer = content if isinstance(content, str) else str(content)
                if answer:
                    log.warning(
                        "content_token_fallback_triggered",
                        answer_len=len(answer),
                    )
                    yield StreamEvent(
                        event=StreamEventType.CONTENT,
                        data=ContentEventData(token=answer),
                    )

    # ------------------------------------------------------------------
    # HITL helpers
    # ------------------------------------------------------------------

    async def _run_inline_ingest(
        self, arxiv_ids: list[str]
    ) -> AsyncIterator[StreamEvent]:
        """Ingest papers inline and yield progress/completion events."""
        total = len(arxiv_ids)
        yield StreamEvent(
            event=StreamEventType.STATUS,
            data=StatusEventData(
                step="ingesting",
                message=f"Ingesting {total} {'paper' if total == 1 else 'papers'}...",
                details={"arxiv_ids": arxiv_ids, "total": total},
            ),
        )

        ingest_start = time.time()
        errors: list[str] = []
        papers_processed = 0
        chunks_created = 0

        if not self.ingest_service:
            log.error("inline_ingest_called_without_service", arxiv_ids=arxiv_ids)
            errors.append("Ingest service unavailable")
        else:
            try:
                response = await self.ingest_service.ingest_by_ids(arxiv_ids)
                papers_processed = response.papers_processed
                chunks_created = response.chunks_created
                errors = [f"[{e.arxiv_id}] {e.error}" for e in response.errors]

                # Track usage so free-tier quota advances
                if papers_processed > 0 and self.usage_counter_repo and self.user_id:
                    await self.usage_counter_repo.increment_ingest_count(
                        self.user_id, papers_processed
                    )
            except Exception as e:
                log.error("inline_ingest_failed", error=str(e), exc_info=True)
                errors.append(str(e))

        duration = time.time() - ingest_start
        yield StreamEvent(
            event=StreamEventType.INGEST_COMPLETE,
            data=IngestCompleteEventData(
                papers_processed=papers_processed,
                chunks_created=chunks_created,
                duration_seconds=round(duration, 2),
                errors=errors,
            ),
        )

    # ------------------------------------------------------------------
    # Main stream orchestration
    # ------------------------------------------------------------------

    async def ask_stream(
        self, query: str, session_id: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """
        Execute agent workflow with streaming events.

        Uses LangGraph's astream with stream_mode=["updates", "custom"].
        Handles HITL interrupts for propose_ingest confirmation.

        Args:
            query: User question
            session_id: Optional session ID for conversation continuity

        Yields:
            StreamEvent objects for status updates, content tokens, sources, and metadata
        """
        start_time = time.time()

        # Generate session_id if not provided (new conversation)
        if not session_id:
            session_id = str(uuid_lib.uuid4())

        # Get turn count for deterministic thread_id (enables checkpoint resume)
        turn_number = 0
        if self.conversation_repo:
            turn_number = await self.conversation_repo.get_turn_count(session_id)
        thread_id = f"{session_id}:{turn_number}"

        log.info(
            "streaming query started",
            query=query[:200],
            session_id=session_id,
            thread_id=thread_id,
            provider=self.context.llm_client.provider_name,
            model=self.context.llm_client.model,
        )

        # Load conversation history if session provided
        history: list[ConversationMessage] = []
        last_guardrail_score: int | None = None
        if session_id and self.conversation_repo:
            turns = await self.conversation_repo.get_history(session_id, self.conversation_window)
            for t in turns:
                history.append({"role": "user", "content": t.user_query})
                history.append({"role": "assistant", "content": t.agent_response})
            if turns:
                last_guardrail_score = turns[-1].guardrail_score
            log.debug("loaded conversation history", session_id=session_id, turns=len(turns))

        # Build LangGraph config with context, thread_id, and Langfuse callback
        config: dict = {"configurable": {"context": self.context, "thread_id": thread_id}}
        trace_id = self._attach_langfuse_callback(
            config, session_id, {"query": query[:200]}
        )

        # Initial state
        initial_state: dict = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "rewritten_query": None,
            "status": "running",
            "iteration": 0,
            "max_iterations": self.context.max_iterations,
            "classification_result": None,
            "evaluation_result": None,
            "tool_history": [],
            "pause_reason": None,
            "pause_data": None,
            "retrieval_attempts": 0,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "tool_outputs": [],
            "metadata": {
                "guardrail_threshold": self.context.guardrail_threshold,
                "top_k": self.context.top_k,
                "reasoning_steps": [],
                "last_guardrail_score": last_guardrail_score,
            },
            "conversation_history": history,
            "session_id": session_id,
        }

        # Track state for final metadata
        final_state: dict = {}
        tracker = _StepTracker()
        interrupted = False
        interrupt_data: dict | None = None

        try:
            # First pass: consume stream
            async for event in self._consume_stream(
                initial_state, config, final_state, tracker
            ):
                if isinstance(event, dict) and "__interrupt__" in event:
                    interrupted = True
                    interrupt_value = event["__interrupt__"]
                    # Extract pause_data from the interrupt value
                    if hasattr(interrupt_value, "__iter__"):
                        for intr in interrupt_value:
                            if hasattr(intr, "value"):
                                interrupt_data = intr.value
                                break
                    if interrupt_data is None:
                        interrupt_data = final_state.get("pause_data")
                    continue
                yield event

            # Handle HITL interrupt: emit proposal, save partial turn, end stream
            if interrupted and interrupt_data:
                papers = interrupt_data.get("papers", [])
                proposed_ids = interrupt_data.get("proposed_ids", [])

                log.info(
                    "hitl_interrupt_detected",
                    session_id=session_id,
                    proposed_papers=len(papers),
                )

                # Emit confirmation request event
                yield StreamEvent(
                    event=StreamEventType.CONFIRM_INGEST,
                    data=ConfirmIngestEventData(
                        papers=papers,
                        session_id=session_id,
                        thread_id=thread_id,
                    ),
                )

                # Save partial turn with pending_confirmation (includes model/temperature
                # so the resume stream can reconstruct the agent service).
                # Explicit commit so the resume request (separate DB session) sees it.
                if self.conversation_repo:
                    partial_turn = await self.conversation_repo.save_turn(
                        session_id,
                        self._build_turn_data(
                            query,
                            final_state,
                            tracker,
                            agent_response="",
                            citations=None,
                            pending_confirmation={
                                "papers": papers,
                                "proposed_ids": proposed_ids,
                                "session_id": session_id,
                                "thread_id": thread_id,
                                "model": self.context.llm_client.model,
                                "temperature": self.context.temperature,
                            },
                        ),
                        user_id=self.user_id,
                    )
                    turn_number = partial_turn.turn_number
                    await self.conversation_repo.commit()

            else:
                # Normal flow: save turn
                if session_id and self.conversation_repo:
                    turn = await self.conversation_repo.save_turn(
                        session_id,
                        self._build_turn_data(query, final_state, tracker),
                        user_id=self.user_id,
                    )
                    turn_number = turn.turn_number

        finally:
            set_trace_context(None)  # Clear trace context

        execution_time = (time.time() - start_time) * 1000

        # Get tool history for metadata
        tool_history = final_state.get("tool_history", [])
        tools_used = [t.tool_name for t in tool_history] if tool_history else []
        classification_result = final_state.get("classification_result")
        guardrail_score = classification_result.scope_score if classification_result else None

        log.info(
            "streaming query complete",
            session_id=session_id,
            iterations=final_state.get("iteration", 0),
            tools_used=tools_used,
            guardrail_score=guardrail_score,
            turn_number=turn_number,
            execution_time_ms=execution_time,
            hitl_interrupted=interrupted,
        )

        # Submit Langfuse scores for analytics
        if trace_id:
            try:
                from src.clients.langfuse_utils import get_langfuse

                langfuse = get_langfuse()
                if langfuse:
                    if guardrail_score is not None:
                        langfuse.score(
                            trace_id=trace_id,
                            name="guardrail_score",
                            value=guardrail_score / 100,
                        )
                    langfuse.score(
                        trace_id=trace_id,
                        name="retrieval_attempts",
                        value=final_state.get("retrieval_attempts", 0),
                    )
            except Exception as e:
                log.warning("langfuse_score_submission_failed", error=str(e), trace_id=trace_id)

        # Final metadata event
        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=query,
                execution_time_ms=execution_time,
                retrieval_attempts=final_state.get("retrieval_attempts", 0),
                rewritten_query=final_state.get("rewritten_query"),
                guardrail_score=guardrail_score,
                provider=self.context.llm_client.provider_name,
                model=self.context.llm_client.model,
                session_id=session_id,
                turn_number=turn_number,
                reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps", []),
                trace_id=trace_id,
            ),
        )

        yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())

    # ------------------------------------------------------------------
    # Resume stream (second leg of two-stream HITL)
    # ------------------------------------------------------------------

    async def resume_stream(
        self,
        session_id: str,
        thread_id: str,
        approved: bool,
        selected_ids: list[str],
    ) -> AsyncIterator[StreamEvent]:
        """
        Resume a paused HITL flow after user confirmation.

        This is the second stream in the two-stream HITL design. It picks up
        from the LangGraph checkpoint saved during ask_stream, runs inline
        ingestion if approved, resumes the graph, and saves a new turn.

        Args:
            session_id: Conversation session ID
            thread_id: LangGraph thread ID for checkpoint resume
            approved: Whether the user approved the ingestion
            selected_ids: arXiv IDs the user selected (empty if declined)

        Yields:
            StreamEvent objects for ingest progress, content, sources, metadata
        """
        start_time = time.time()

        log.info(
            "resume_stream_started",
            session_id=session_id,
            thread_id=thread_id,
            approved=approved,
            selected_count=len(selected_ids),
        )

        # Fetch the pending turn once -- used for double-confirm guard and later cleanup.
        pending_turn_number: int | None = None
        if self.conversation_repo:
            pending_turn = await self.conversation_repo.get_pending_turn(
                session_id, self.user_id
            )
            if not pending_turn or not pending_turn.pending_confirmation:
                log.warning("resume_stream_double_confirm", session_id=session_id)
                yield StreamEvent(
                    event=StreamEventType.ERROR,
                    data=ErrorEventData(
                        error="This proposal has already been processed.",
                        code="DOUBLE_CONFIRM",
                    ),
                )
                yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())
                return
            pending_turn_number = pending_turn.turn_number

        # Build resume value
        if approved:
            papers_processed = 0
            ingest_errors: list[str] = []
            async for ingest_event in self._run_inline_ingest(selected_ids):
                if isinstance(ingest_event.data, IngestCompleteEventData):
                    papers_processed = ingest_event.data.papers_processed
                    ingest_errors = ingest_event.data.errors
                yield ingest_event

            resume_value: dict = {
                "approved": True,
                "selected_ids": selected_ids,
                "papers_processed": papers_processed,
                "errors": ingest_errors,
            }
            synthetic_query = (
                f"Confirmed ingestion of {len(selected_ids)} "
                f"{'paper' if len(selected_ids) == 1 else 'papers'}"
            )
        else:
            resume_value = {"declined": True}
            synthetic_query = "Declined paper ingestion"

        # Build config and resume graph from checkpoint
        config: dict = {"configurable": {"context": self.context, "thread_id": thread_id}}
        trace_id = self._attach_langfuse_callback(
            config, session_id, {"resume": True, "approved": approved}
        )

        final_state: dict = {}
        tracker = _StepTracker()
        turn_number = 0

        try:
            async for event in self._consume_stream(
                Command(resume=resume_value),
                config,
                final_state,
                tracker,
                sources_emitted=True,
            ):
                if isinstance(event, dict) and "__interrupt__" in event:
                    continue  # Ignore nested interrupts
                yield event
        except (RuntimeError, ValueError) as e:
            if not any(p in str(e).lower() for p in _CHECKPOINT_ERROR_PATTERNS):
                raise
            log.warning(
                "resume_stream_checkpoint_expired",
                session_id=session_id,
                thread_id=thread_id,
            )
            if self.conversation_repo and pending_turn_number is not None:
                await self.conversation_repo.clear_pending_confirmation(
                    session_id, pending_turn_number
                )
            yield StreamEvent(
                event=StreamEventType.ERROR,
                data=ErrorEventData(
                    error="The confirmation window has expired. Please try again.",
                    code="CHECKPOINT_EXPIRED",
                ),
            )
            yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())
            return
        finally:
            set_trace_context(None)

        # Save new turn for the resume response, then clear the original proposal turn.
        if self.conversation_repo:
            turn = await self.conversation_repo.save_turn(
                session_id,
                self._build_turn_data(synthetic_query, final_state, tracker),
                user_id=self.user_id,
            )
            turn_number = turn.turn_number

            if pending_turn_number is not None:
                await self.conversation_repo.clear_pending_confirmation(
                    session_id, pending_turn_number
                )

        execution_time = (time.time() - start_time) * 1000

        log.info(
            "resume_stream_complete",
            session_id=session_id,
            approved=approved,
            turn_number=turn_number,
            execution_time_ms=execution_time,
        )

        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=synthetic_query,
                execution_time_ms=execution_time,
                retrieval_attempts=final_state.get("retrieval_attempts", 0),
                rewritten_query=None,
                guardrail_score=None,
                provider=self.context.llm_client.provider_name,
                model=self.context.llm_client.model,
                session_id=session_id,
                turn_number=turn_number,
                reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps", []),
                trace_id=trace_id,
            ),
        )

        yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_langfuse_callback(
        self,
        config: dict,
        session_id: str | None,
        extra_metadata: dict | None = None,
    ) -> str | None:
        """Attach a Langfuse callback to the LangGraph config if enabled.

        Returns the trace_id if a callback was attached, else None.
        """
        if not LANGFUSE_CALLBACK_AVAILABLE:
            return None
        settings = get_settings()
        if not settings.langfuse_enabled:
            return None
        metadata = {
            "provider": self.context.llm_client.provider_name,
            "model": self.context.llm_client.model,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        callback = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=session_id,
            user_id=str(self.user_id) if self.user_id else session_id,
            metadata=metadata,
        )
        config["callbacks"] = [callback]
        set_trace_context(callback.trace_id)
        return callback.trace_id

    @staticmethod
    def _extract_answer(final_state: dict) -> str:
        """Extract the final answer text from the last AIMessage in state."""
        if final_state.get("messages"):
            last_msg = final_state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                content = last_msg.content
                return content if isinstance(content, str) else str(content)
        return ""

    def _build_sources_dicts(self, final_state: dict) -> list[dict]:
        """Build sources list from final state for persistence."""
        relevant_chunks = final_state.get("relevant_chunks", [])[: self.context.top_k]
        return [
            {
                "arxiv_id": chunk["arxiv_id"],
                "title": chunk["title"],
                "authors": chunk.get("authors", []),
                "pdf_url": chunk.get("pdf_url", f"https://arxiv.org/pdf/{chunk['arxiv_id']}.pdf"),
                "relevance_score": chunk.get("score", 0.0),
                "published_date": chunk.get("published_date"),
                "was_graded_relevant": True,
            }
            for chunk in relevant_chunks
        ]

    @staticmethod
    def _extract_citations(final_state: dict) -> dict | None:
        """Extract citations from explore_citations tool output, if present."""
        for tool_output in final_state.get("tool_outputs", []):
            if tool_output.get("tool_name") == "explore_citations" and tool_output.get("data"):
                return tool_output["data"]
        return None

    def _build_turn_data(
        self,
        query: str,
        final_state: dict,
        tracker: _StepTracker,
        **overrides,
    ) -> TurnData:
        """Build TurnData from final state with optional field overrides."""
        classification_result = final_state.get("classification_result")
        sources = self._build_sources_dicts(final_state)
        # Allow callers to override citations (e.g. None for partial HITL saves)
        citations = overrides.pop("citations", self._extract_citations(final_state))
        agent_response = overrides.pop("agent_response", self._extract_answer(final_state))

        return TurnData(
            user_query=query,
            agent_response=agent_response,
            provider=self.context.llm_client.provider_name,
            model=self.context.llm_client.model,
            guardrail_score=classification_result.scope_score if classification_result else None,
            retrieval_attempts=final_state.get("retrieval_attempts", 0),
            rewritten_query=final_state.get("rewritten_query"),
            sources=sources or None,
            reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps"),
            thinking_steps=tracker.steps or None,
            citations=citations,
            **overrides,
        )
