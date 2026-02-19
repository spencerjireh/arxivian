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
)
from src.schemas.common import SourceInfo
from src.utils.logger import get_logger
from .context import AgentContext

log = get_logger(__name__)

# Map LangGraph node names to user-friendly step names
NODE_TO_STEP = {
    "guardrail": "guardrail",
    "out_of_scope": "out_of_scope",
    "router": "routing",
    "executor": "executing",
    "grade_documents": "grading",
    "generate": "generation",
}

NODE_MESSAGES = {
    "guardrail": "Validating query relevance...",
    "out_of_scope": "Generating out-of-scope response...",
    "router": "Deciding next action...",
    "grade_documents": "Grading document relevance...",
    "generate": "Generating answer...",
}

# Nodes whose on_chain_start is suppressed (they emit their own start events)
_SKIP_CHAIN_START = {"executor"}


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
        self.steps.append({
            "step": step,
            "message": message,
            "details": details,
            "tool_name": (details or {}).get("tool_name"),
            "started_at": datetime.fromtimestamp(
                started, tz=timezone.utc
            ).isoformat(),
            "completed_at": datetime.fromtimestamp(
                now, tz=timezone.utc
            ).isoformat(),
        })


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
        ingest_service: IngestService | None = None,
        arxiv_client: ArxivClient | None = None,
        paper_repository: PaperRepository | None = None,
        conversation_repo: ConversationRepository | None = None,
        conversation_window: int = 5,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        max_iterations: int = 5,
        temperature: float = 0.3,
        user_id: UUID | None = None,
        daily_ingests: int | None = None,
        usage_counter_repo: UsageCounterRepository | None = None,
    ):
        self.graph = graph
        self.context = AgentContext(
            llm_client=llm_client,
            search_service=search_service,
            ingest_service=ingest_service,
            arxiv_client=arxiv_client,
            paper_repository=paper_repository,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
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

    async def ask_stream(
        self, query: str, session_id: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """
        Execute agent workflow with streaming events via astream_events.

        Yields SSE events for each workflow step and content tokens.

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

        # Fresh thread_id per invocation: isolates checkpoint state so each request
        # starts clean. Conversation continuity is handled by ConversationRepository,
        # not the checkpointer. Future interrupt/resume features can reuse thread_id.
        thread_id = str(uuid_lib.uuid4())

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
        trace_id: str | None = None

        if LANGFUSE_CALLBACK_AVAILABLE:
            settings = get_settings()
            if settings.langfuse_enabled:
                callback = CallbackHandler(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                    session_id=session_id,
                    user_id=str(self.user_id) if self.user_id else session_id,
                    metadata={
                        "query": query[:200],
                        "provider": self.context.llm_client.provider_name,
                        "model": self.context.llm_client.model,
                    },
                )
                trace_id = callback.trace_id
                config["callbacks"] = [callback]
                set_trace_context(trace_id)  # Propagate trace to LLM client

        # Initial state with new router architecture fields
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "rewritten_query": None,
            # Router architecture fields
            "status": "running",
            "iteration": 0,
            "max_iterations": self.context.max_iterations,
            "router_decision": None,
            "tool_history": [],
            "pause_reason": None,
            # Legacy fields (kept for grading)
            "retrieval_attempts": 0,
            "guardrail_result": None,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "grading_results": [],
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
        sources_emitted = False
        content_tokens_emitted = 0
        tracker = _StepTracker()

        try:
            async for event in self.graph.astream_events(
                initial_state, version="v2", config=config
            ):
                kind = event["event"]

                # Node start - emit status event (skip nodes covered by custom events)
                if kind == "on_chain_start" and event["name"] in NODE_TO_STEP:
                    node_name = event["name"]
                    if node_name in _SKIP_CHAIN_START:
                        continue
                    step = NODE_TO_STEP[node_name]
                    message = NODE_MESSAGES.get(node_name, f"Processing {node_name}...")

                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(step=step, message=message),
                    )
                    tracker.start(step)

                # Node end - extract state updates and emit detailed status
                elif kind == "on_chain_end" and event["name"] in NODE_TO_STEP:
                    node_name = event["name"]
                    output = event.get("data", {}).get("output", {})

                    # Update final_state with latest output
                    if isinstance(output, dict):
                        final_state.update(output)

                    # Emit detailed status after guardrail
                    if node_name == "guardrail" and output.get("guardrail_result"):
                        result = output["guardrail_result"]
                        is_in_scope = result.score >= self.context.guardrail_threshold
                        guardrail_details = {
                            "score": result.score,
                            "threshold": self.context.guardrail_threshold,
                            "reasoning": result.reasoning,
                        }
                        guardrail_msg = (
                            f"Query {'is in scope' if is_in_scope else 'is out of scope'}"
                        )
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="guardrail",
                                message=guardrail_msg,
                                details=guardrail_details,
                            ),
                        )
                        tracker.end("guardrail", guardrail_msg, guardrail_details)

                    # Emit router decision details
                    elif node_name == "router" and output.get("router_decision"):
                        decision = output["router_decision"]
                        routing_details = {
                            "action": decision.action,
                            "tools": [tc.tool_name for tc in decision.tool_calls],
                            "iteration": output.get("iteration", 0),
                            "reasoning": decision.reasoning,
                        }
                        routing_msg = f"Decided to {decision.action}"
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="routing",
                                message=routing_msg,
                                details=routing_details,
                            ),
                        )
                        tracker.end("routing", routing_msg, routing_details)

                        # Emit tool_start for each planned tool (chain-level
                        # fallback -- custom events from asyncio.gather in
                        # the executor may not propagate through astream_events)
                        for tc in decision.tool_calls:
                            tool_details = {"tool_name": tc.tool_name}
                            tool_msg = f"Calling {tc.tool_name}..."
                            yield StreamEvent(
                                event=StreamEventType.STATUS,
                                data=StatusEventData(
                                    step="executing",
                                    message=tool_msg,
                                    details=tool_details,
                                ),
                            )
                            tracker.start("executing", tool_details)

                    # Emit tool completion from executor chain_end
                    # (chain-level fallback for custom events that may not
                    # propagate from asyncio.gather)
                    elif node_name == "executor":
                        last_tools = output.get("last_executed_tools", [])
                        tool_history = output.get("tool_history", [])
                        recent = tool_history[-len(last_tools):] if last_tools else []
                        for exec_record in recent:
                            ok = exec_record.success
                            status = "completed" if ok else "failed"
                            tool_end_msg = f"{exec_record.tool_name} {status}"
                            tool_details = {
                                "tool_name": exec_record.tool_name,
                                "success": ok,
                            }
                            yield StreamEvent(
                                event=StreamEventType.STATUS,
                                data=StatusEventData(
                                    step="executing",
                                    message=tool_end_msg,
                                    details=tool_details,
                                ),
                            )
                            tracker.end("executing", tool_end_msg, tool_details)

                    # Emit out-of-scope completion
                    elif node_name == "out_of_scope":
                        tracker.end("out_of_scope", "Out of scope", None)

                    # Emit generation completion
                    elif node_name == "generate":
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="generation",
                                message="Generation complete",
                            ),
                        )
                        tracker.end("generation", "Generation complete", None)

                    # Emit grading results
                    elif node_name == "grade_documents":
                        relevant = output.get("relevant_chunks", [])
                        total = output.get("grading_results", [])
                        grading_details = {
                            "relevant": len(relevant),
                            "total": len(total),
                        }
                        grading_msg = f"Found {len(relevant)} relevant documents"
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="grading",
                                message=grading_msg,
                                details=grading_details,
                            ),
                        )
                        tracker.end("grading", grading_msg, grading_details)

                        # Emit sources after grading (before generation)
                        if not sources_emitted and relevant:
                            sources = [
                                SourceInfo(
                                    arxiv_id=chunk["arxiv_id"],
                                    title=chunk["title"],
                                    authors=chunk.get("authors", []),
                                    pdf_url=chunk.get(
                                        "pdf_url", f"https://arxiv.org/pdf/{chunk['arxiv_id']}.pdf"
                                    ),
                                    relevance_score=chunk.get("score", 0.0),
                                    published_date=chunk.get("published_date"),
                                    was_graded_relevant=True,
                                )
                                for chunk in relevant[: self.context.top_k]
                            ]
                            yield StreamEvent(
                                event=StreamEventType.SOURCES,
                                data=SourcesEventData(sources=sources),
                            )
                            sources_emitted = True

                # Stream custom events (tokens from our LLM client)
                elif kind == "on_custom_event" and event.get("name") == "token":
                    token = event.get("data")
                    if token and isinstance(token, str):
                        content_tokens_emitted += 1
                        yield StreamEvent(
                            event=StreamEventType.CONTENT,
                            data=ContentEventData(token=token),
                        )

                # Tool start/end events are emitted at chain level (router/executor on_chain_end).
        finally:
            set_trace_context(None)  # Clear trace context

        # Extract final answer from state
        answer = ""
        if final_state.get("messages"):
            last_msg = final_state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                content = last_msg.content
                answer = content if isinstance(content, str) else str(content)

        # Fallback: emit answer as single CONTENT event if no tokens streamed
        # (on_custom_event may not propagate in all event loop contexts)
        if content_tokens_emitted == 0 and answer:
            log.warning(
                "content_token_fallback_triggered",
                answer_len=len(answer),
                session_id=session_id,
            )
            yield StreamEvent(
                event=StreamEventType.CONTENT,
                data=ContentEventData(token=answer),
            )

        # Build sources for persistence
        relevant_chunks = final_state.get("relevant_chunks", [])[: self.context.top_k]
        sources_dicts = [
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

        # Save turn to database
        turn_number = 0
        guardrail_result = final_state.get("guardrail_result")
        guardrail_score = guardrail_result.score if guardrail_result else None

        if session_id and self.conversation_repo:
            turn = await self.conversation_repo.save_turn(
                session_id,
                TurnData(
                    user_query=query,
                    agent_response=answer,
                    provider=self.context.llm_client.provider_name,
                    model=self.context.llm_client.model,
                    guardrail_score=guardrail_score,
                    retrieval_attempts=final_state.get("retrieval_attempts", 0),
                    rewritten_query=final_state.get("rewritten_query"),
                    sources=sources_dicts if sources_dicts else None,
                    reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps"),
                    thinking_steps=tracker.steps or None,
                ),
                user_id=self.user_id,
            )
            turn_number = turn.turn_number

        execution_time = (time.time() - start_time) * 1000

        # Get tool history for metadata
        tool_history = final_state.get("tool_history", [])
        tools_used = [t.tool_name for t in tool_history] if tool_history else []

        log.info(
            "streaming query complete",
            session_id=session_id,
            sources=len(sources_dicts),
            iterations=final_state.get("iteration", 0),
            tools_used=tools_used,
            guardrail_score=guardrail_score,
            turn_number=turn_number,
            answer_len=len(answer),
            execution_time_ms=execution_time,
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
                            value=guardrail_score / 100,  # Normalize to 0-1
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

        yield StreamEvent(event=StreamEventType.DONE, data={})
