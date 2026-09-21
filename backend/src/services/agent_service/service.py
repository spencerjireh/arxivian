"""Agent service with LangGraph workflow (paper-scoped chat)."""

from __future__ import annotations

import time
import uuid as uuid_lib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

import logfire
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.clients.base_llm_client import BaseLLMClient
from src.clients.semantic_scholar_client import SemanticScholarClient
from src.repositories.conversation_repository import ConversationRepository, TurnData
from src.repositories.paper_repository import PaperRepository
from src.schemas.stream import (
    CitationsEventData,
    ContentEventData,
    DoneEventData,
    MetadataEventData,
    SourceInfo,
    SourcesEventData,
    StatusEventData,
    StreamEvent,
    StreamEventType,
)
from src.services.agent_service.state import ConversationMessage
from src.services.agent_service.title import generate_title
from src.services.search_service import SearchService
from src.utils.logger import get_logger

from .context import AgentContext, ScopedPaper

log = get_logger(__name__)

# Map LangGraph node names to user-facing step names
NODE_TO_STEP = {
    "classify_and_route": "classifying",
    "out_of_scope": "out_of_scope",
    "executor": "executing",
    "evaluate_batch": "evaluating",
    "generate": "generation",
}

NODE_MESSAGES = {
    "classify_and_route": "Classifying query...",
    "out_of_scope": "Generating out-of-scope response...",
    "evaluate_batch": "Evaluating retrieval quality...",
    "generate": "Generating answer...",
}

# Nodes whose start event is synthesized from custom events instead
_SKIP_START_STATUS = {"executor"}


class AgentService:
    """Runs the paper-scoped agent graph and translates it into SSE events."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        graph: CompiledStateGraph,
        scoped_paper: ScopedPaper,
        db_session: AsyncSession | None = None,
        semantic_scholar_client: SemanticScholarClient | None = None,
        paper_repository: PaperRepository | None = None,
        conversation_repo: ConversationRepository | None = None,
        conversation_window: int = 5,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_iterations: int = 5,
        temperature: float = 0.3,
        user_id: UUID | None = None,
    ):
        self.graph = graph
        self.scoped_paper = scoped_paper
        self.context = AgentContext(
            llm_client=llm_client,
            search_service=search_service,
            scoped_paper=scoped_paper,
            db_session=db_session,
            semantic_scholar_client=semantic_scholar_client,
            paper_repository=paper_repository,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
            max_iterations=max_iterations,
            temperature=temperature,
        )
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Stream consumption: translates LangGraph astream events to SSE
    # ------------------------------------------------------------------

    async def _consume_stream(
        self, input_data: dict, config: dict, final_state: dict
    ) -> AsyncIterator[StreamEvent]:
        """Consume graph.astream and yield StreamEvent objects."""
        seen_nodes: set[str] = set()
        content_tokens_emitted = 0
        sources_emitted = False

        async for stream_mode, chunk in self.graph.astream(
            input_data,
            config,
            stream_mode=["updates", "custom"],
        ):
            if not isinstance(chunk, dict):
                continue

            if stream_mode == "custom":
                # Custom events from get_stream_writer()
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
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="executing",
                            message=f"Calling {tool_name}...",
                            details={"tool_name": tool_name},
                        ),
                    )

                elif event_type == "tool_end":
                    tool_name = chunk.get("tool_name", "")
                    success = chunk.get("success", True)
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="executing",
                            message=f"{tool_name} {'completed' if success else 'failed'}",
                            details={"tool_name": tool_name, "success": success},
                        ),
                    )

                elif event_type == "citations_data":
                    citations = chunk.get("data", {})
                    yield StreamEvent(
                        event=StreamEventType.CITATIONS,
                        data=CitationsEventData(**citations),
                    )

            elif stream_mode == "updates":
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
                        seen_nodes.add(node_name)

                    if isinstance(output, dict):
                        final_state.update(output)

                    # Emit detailed status per node
                    if node_name == "classify_and_route" and output.get("classification_result"):
                        result = output["classification_result"]
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="classifying",
                                message=(
                                    f"Classified: intent={result.intent}, "
                                    f"score={result.scope_score}"
                                ),
                                details={
                                    "score": result.scope_score,
                                    "intent": result.intent,
                                    "threshold": self.context.guardrail_threshold,
                                    "reasoning": result.reasoning,
                                },
                            ),
                        )

                    elif node_name == "generate":
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(step="generation", message="Generation complete"),
                        )

                    elif node_name == "evaluate_batch":
                        eval_result = output.get("evaluation_result")
                        relevant = output.get("relevant_chunks", [])
                        sufficient = bool(eval_result and eval_result.sufficient)
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="evaluating",
                                message=(
                                    f"Evaluation: {'sufficient' if sufficient else 'insufficient'}"
                                ),
                                details={
                                    "sufficient": eval_result.sufficient if eval_result else None,
                                    "total": len(final_state.get("retrieved_chunks", [])),
                                    "reasoning": eval_result.reasoning if eval_result else "",
                                },
                            ),
                        )

                        # Emit sources after evaluation (before generation)
                        if not sources_emitted and relevant:
                            sources = [
                                SourceInfo(**s) for s in self._build_sources_dicts(final_state)
                            ]
                            yield StreamEvent(
                                event=StreamEventType.SOURCES,
                                data=SourcesEventData(sources=sources),
                            )
                            sources_emitted = True

        # Fallback: emit answer as single CONTENT event if no tokens streamed
        if content_tokens_emitted == 0:
            answer = self._extract_answer(final_state)
            if answer:
                log.warning("content_token_fallback_triggered", answer_len=len(answer))
                yield StreamEvent(
                    event=StreamEventType.CONTENT,
                    data=ContentEventData(token=answer),
                )

    # ------------------------------------------------------------------
    # Main stream orchestration
    # ------------------------------------------------------------------

    async def ask_stream(
        self, query: str, session_id: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Execute the agent workflow for one turn, streaming events.

        Args:
            query: User question
            session_id: Optional session ID for conversation continuity

        Yields:
            StreamEvent objects for status updates, content tokens, sources, and metadata
        """
        start_time = time.time()
        session_id = session_id or str(uuid_lib.uuid4())

        log.info(
            "streaming query started",
            query=query[:200],
            session_id=session_id,
            model=self.context.llm_client.model,
            scoped_arxiv_id=self.scoped_paper.arxiv_id,
        )

        # Load conversation history if session provided
        history: list[ConversationMessage] = []
        last_guardrail_score: int | None = None
        if self.conversation_repo:
            turns = await self.conversation_repo.get_history(
                session_id, self.conversation_window, user_id=self.user_id
            )
            for t in turns:
                history.append({"role": "user", "content": t.user_query})
                history.append({"role": "assistant", "content": t.agent_response})
            if turns:
                last_guardrail_score = turns[-1].guardrail_score
            log.debug("loaded conversation history", session_id=session_id, turns=len(turns))

        config: dict = {"configurable": {"context": self.context}}
        span = logfire.span(
            "chat.turn",
            session_id=session_id,
            arxiv_id=self.scoped_paper.arxiv_id,
            model=self.context.llm_client.model,
        )
        span.__enter__()

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

        final_state: dict = {}
        turn_number = 0

        try:
            async for event in self._consume_stream(initial_state, config, final_state):
                yield event

            if self.conversation_repo:
                turn = await self.conversation_repo.save_turn(
                    session_id,
                    self._build_turn_data(query, final_state),
                    user_id=self.user_id,
                    paper_id=UUID(self.scoped_paper.paper_id),
                )
                turn_number = turn.turn_number

                if turn_number == 0:
                    title = await generate_title(self.context.llm_client, query)
                    if title:
                        await self.conversation_repo.update_title(
                            session_id, title, user_id=self.user_id
                        )

        except BaseException as exc:
            span.__exit__(type(exc), exc, exc.__traceback__)
            raise

        execution_time = (time.time() - start_time) * 1000

        tool_history = final_state.get("tool_history", [])
        tools_used = [t.tool_name for t in tool_history]
        classification_result = final_state.get("classification_result")
        guardrail_score = classification_result.scope_score if classification_result else None
        retrieval_attempts = final_state.get("retrieval_attempts", 0)

        # Turn-level outcome attributes (previously separate tracing scores).
        span.set_attributes(
            {
                "guardrail_score": guardrail_score,
                "retrieval_attempts": retrieval_attempts,
                "tools_used": tools_used,
                "turn_number": turn_number,
                "iterations": final_state.get("iteration", 0),
            }
        )
        span.__exit__(None, None, None)

        log.info(
            "streaming query complete",
            session_id=session_id,
            iterations=final_state.get("iteration", 0),
            tools_used=tools_used,
            guardrail_score=guardrail_score,
            turn_number=turn_number,
            execution_time_ms=execution_time,
        )

        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=query,
                execution_time_ms=execution_time,
                retrieval_attempts=retrieval_attempts,
                guardrail_score=guardrail_score,
                session_id=session_id,
                turn_number=turn_number,
            ),
        )

        yield StreamEvent(event=StreamEventType.DONE, data=DoneEventData())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        """Build sources list from the graded chunks (top_k) for events and persistence."""
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

    def _build_turn_data(self, query: str, final_state: dict) -> TurnData:
        """Build TurnData from the final graph state."""
        classification_result = final_state.get("classification_result")
        sources = self._build_sources_dicts(final_state)
        return TurnData(
            user_query=query,
            agent_response=self._extract_answer(final_state),
            provider=self.context.llm_client.provider_name,
            model=self.context.llm_client.model,
            guardrail_score=classification_result.scope_score if classification_result else None,
            retrieval_attempts=final_state.get("retrieval_attempts", 0),
            rewritten_query=final_state.get("rewritten_query"),
            sources=sources or None,
            reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps"),
            citations=self._extract_citations(final_state),
        )
