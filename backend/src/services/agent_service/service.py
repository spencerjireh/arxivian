"""Agent service with LangGraph workflow."""

import time
import uuid
from typing import AsyncIterator

from langchain_core.messages import HumanMessage, AIMessage

from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.conversation import ConversationMessage, TurnData
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
from .graph_builder import build_agent_graph

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
    "executor": "Executing tool...",
    "grade_documents": "Grading document relevance...",
    "generate": "Generating answer...",
}


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
        conversation_repo: ConversationRepository | None = None,
        conversation_window: int = 5,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        max_iterations: int = 5,
        temperature: float = 0.3,
    ):
        self.graph = build_agent_graph(
            llm_client=llm_client,
            search_service=search_service,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
            max_retrieval_attempts=max_retrieval_attempts,
            max_iterations=max_iterations,
            temperature=temperature,
        )
        self.llm_client = llm_client
        self.search_service = search_service
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.max_iterations = max_iterations
        self.temperature = temperature

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
            session_id = str(uuid.uuid4())

        log.info(
            "streaming query started",
            query=query[:200],
            session_id=session_id,
            provider=self.llm_client.provider_name,
            model=self.llm_client.model,
        )

        # Load conversation history if session provided
        history: list[ConversationMessage] = []
        if session_id and self.conversation_repo:
            turns = await self.conversation_repo.get_history(session_id, self.conversation_window)
            for t in turns:
                history.append({"role": "user", "content": t.user_query})
                history.append({"role": "assistant", "content": t.agent_response})
            log.debug("loaded conversation history", session_id=session_id, turns=len(turns))

        # Initial state with new router architecture fields
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "rewritten_query": None,
            # Router architecture fields
            "status": "running",
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "router_decision": None,
            "tool_history": [],
            "pause_reason": None,
            # Legacy fields (kept for grading)
            "retrieval_attempts": 0,
            "guardrail_result": None,
            "routing_decision": None,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "grading_results": [],
            "metadata": {
                "guardrail_threshold": self.guardrail_threshold,
                "top_k": self.top_k,
                "reasoning_steps": [],
            },
            "conversation_history": history,
            "session_id": session_id,
        }

        # Track state for final metadata
        final_state: dict = {}
        sources_emitted = False

        async for event in self.graph.astream_events(initial_state, version="v2"):
            kind = event["event"]

            # Node start - emit status event
            if kind == "on_chain_start" and event["name"] in NODE_TO_STEP:
                node_name = event["name"]
                step = NODE_TO_STEP[node_name]
                message = NODE_MESSAGES.get(node_name, f"Processing {node_name}...")

                yield StreamEvent(
                    event=StreamEventType.STATUS,
                    data=StatusEventData(step=step, message=message),
                )

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
                    is_in_scope = result.score >= self.guardrail_threshold
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="guardrail",
                            message=f"Query {'is in scope' if is_in_scope else 'is out of scope'}",
                            details={
                                "score": result.score,
                                "threshold": self.guardrail_threshold,
                                "reasoning": result.reasoning,
                            },
                        ),
                    )

                # Emit router decision details
                elif node_name == "router" and output.get("router_decision"):
                    decision = output["router_decision"]
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="routing",
                            message=f"Decided to {decision.action}",
                            details={
                                "action": decision.action,
                                "tool": decision.tool_name,
                                "iteration": output.get("iteration", 0),
                                "reasoning": decision.reasoning,
                            },
                        ),
                    )

                # Emit executor tool details
                elif node_name == "executor" and output.get("tool_history"):
                    tool_history = output["tool_history"]
                    if tool_history:
                        last_exec = tool_history[-1]
                        yield StreamEvent(
                            event=StreamEventType.STATUS,
                            data=StatusEventData(
                                step="executing",
                                message=f"Executed {last_exec.tool_name}",
                                details={
                                    "tool": last_exec.tool_name,
                                    "success": last_exec.success,
                                    "result": last_exec.result_summary,
                                },
                            ),
                        )

                # Emit grading results
                elif node_name == "grade_documents":
                    relevant = output.get("relevant_chunks", [])
                    total = output.get("retrieved_chunks", [])
                    yield StreamEvent(
                        event=StreamEventType.STATUS,
                        data=StatusEventData(
                            step="grading",
                            message=f"Found {len(relevant)} relevant documents",
                            details={"relevant": len(relevant), "total": len(total)},
                        ),
                    )

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
                            for chunk in relevant[: self.top_k]
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
                    yield StreamEvent(
                        event=StreamEventType.CONTENT,
                        data=ContentEventData(token=token),
                    )

            # Handle tool events from executor
            elif kind == "on_custom_event" and event.get("name") == "tool_start":
                data = event.get("data", {})
                yield StreamEvent(
                    event=StreamEventType.STATUS,
                    data=StatusEventData(
                        step="executing",
                        message=f"Calling {data.get('tool_name', 'tool')}...",
                        details=data,
                    ),
                )

            elif kind == "on_custom_event" and event.get("name") == "tool_end":
                data = event.get("data", {})
                status = "completed" if data.get("success") else "failed"
                yield StreamEvent(
                    event=StreamEventType.STATUS,
                    data=StatusEventData(
                        step="executing",
                        message=f"Tool {status}",
                        details=data,
                    ),
                )

        # Extract final answer from state
        answer = ""
        if final_state.get("messages"):
            last_msg = final_state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                content = last_msg.content
                answer = content if isinstance(content, str) else str(content)

        # Build sources for persistence
        relevant_chunks = final_state.get("relevant_chunks", [])[: self.top_k]
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
                    provider=self.llm_client.provider_name,
                    model=self.llm_client.model,
                    guardrail_score=guardrail_score,
                    retrieval_attempts=final_state.get("retrieval_attempts", 0),
                    rewritten_query=final_state.get("rewritten_query"),
                    sources=sources_dicts if sources_dicts else None,
                    reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps"),
                ),
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

        # Final metadata event
        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=query,
                execution_time_ms=execution_time,
                retrieval_attempts=final_state.get("retrieval_attempts", 0),
                rewritten_query=final_state.get("rewritten_query"),
                guardrail_score=guardrail_score,
                provider=self.llm_client.provider_name,
                model=self.llm_client.model,
                session_id=session_id,
                turn_number=turn_number,
                reasoning_steps=final_state.get("metadata", {}).get("reasoning_steps", []),
            ),
        )

        yield StreamEvent(event=StreamEventType.DONE, data={})
