"""Agent service with LangGraph workflow."""

from typing import AsyncIterator

from langchain_core.messages import HumanMessage

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
from src.schemas.langgraph_state import GuardrailScoring, GradingResult
from src.utils.logger import get_logger
from .graph_builder import build_agent_graph
from .context import ConversationFormatter
from .prompts import (
    PromptBuilder,
    ANSWER_SYSTEM_PROMPT,
    OUT_OF_SCOPE_SYSTEM_PROMPT,
    get_guardrail_prompt,
    get_grading_prompt,
    get_rewrite_prompt,
)

log = get_logger(__name__)


class AgentService:
    """
    Service for executing agent workflows.

    Wraps LangGraph workflow with a clean interface.
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
        temperature: float = 0.3,
    ):
        self.graph = build_agent_graph(
            llm_client=llm_client,
            search_service=search_service,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
            max_retrieval_attempts=max_retrieval_attempts,
            temperature=temperature,
        )
        self.llm_client = llm_client
        self.search_service = search_service
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.temperature = temperature
        self.conversation_formatter = ConversationFormatter(max_turns=conversation_window)

    async def ask(self, query: str, session_id: str | None = None) -> dict:
        """
        Execute agent workflow.

        Args:
            query: User question
            session_id: Optional session ID for conversation continuity

        Returns:
            Dict with answer, sources, reasoning steps, etc.
        """
        log.info(
            "agent query started",
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

        # Initial state
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "original_query": None,
            "rewritten_query": None,
            "retrieval_attempts": 0,
            "guardrail_result": None,
            "routing_decision": None,
            "retrieved_chunks": [],
            "relevant_chunks": [],
            "grading_results": [],
            "metadata": {"guardrail_threshold": self.guardrail_threshold, "reasoning_steps": []},
            "conversation_history": history,
            "session_id": session_id,
        }

        # Run graph
        result = await self.graph.ainvoke(initial_state)

        # Extract answer from final message
        answer = result["messages"][-1].content

        # Build sources
        sources = [
            {
                "arxiv_id": chunk["arxiv_id"],
                "title": chunk["title"],
                "authors": chunk["authors"],
                "pdf_url": chunk["pdf_url"],
                "relevance_score": chunk["score"],
                "published_date": chunk.get("published_date"),
                "was_graded_relevant": True,
            }
            for chunk in result["relevant_chunks"][: self.top_k]
        ]

        # Save turn if session provided
        turn_number = 0
        if session_id and self.conversation_repo:
            turn = await self.conversation_repo.save_turn(
                session_id,
                TurnData(
                    user_query=query,
                    agent_response=answer,
                    provider=self.llm_client.provider_name,
                    model=self.llm_client.model,
                    guardrail_score=(
                        result["guardrail_result"].score if result["guardrail_result"] else None
                    ),
                    retrieval_attempts=result.get("retrieval_attempts", 1),
                    rewritten_query=result.get("rewritten_query"),
                    sources=sources,
                    reasoning_steps=result.get("metadata", {}).get("reasoning_steps"),
                ),
            )
            turn_number = turn.turn_number

        guardrail_score = result["guardrail_result"].score if result["guardrail_result"] else None

        log.info(
            "agent query complete",
            session_id=session_id,
            sources=len(sources),
            retrieval_attempts=result["retrieval_attempts"],
            guardrail_score=guardrail_score,
            turn_number=turn_number,
            answer_len=len(answer),
        )

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "reasoning_steps": result["metadata"]["reasoning_steps"],
            "retrieval_attempts": result["retrieval_attempts"],
            "rewritten_query": result.get("rewritten_query"),
            "guardrail_score": guardrail_score,
            "provider": self.llm_client.provider_name,
            "model": self.llm_client.model,
            "session_id": session_id,
            "turn_number": turn_number,
        }

    async def ask_stream(
        self, query: str, session_id: str | None = None
    ) -> AsyncIterator[StreamEvent]:
        """
        Execute agent workflow with streaming events.

        Yields SSE events for each workflow step and content tokens.

        Args:
            query: User question
            session_id: Optional session ID for conversation continuity

        Yields:
            StreamEvent objects for status updates, content tokens, sources, and metadata
        """
        import time
        import asyncio

        start_time = time.time()
        reasoning_steps: list[str] = []

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

        # Step 1: Guardrail
        yield StreamEvent(
            event=StreamEventType.STATUS,
            data=StatusEventData(
                step="guardrail",
                message="Validating query relevance...",
            ),
        )

        guardrail_prompt = get_guardrail_prompt(query, self.guardrail_threshold)
        guardrail_result: GuardrailScoring = await self.llm_client.generate_structured(
            messages=[{"role": "user", "content": guardrail_prompt}],
            response_format=GuardrailScoring,
        )

        reasoning_steps.append(f"Validated query scope (score: {guardrail_result.score}/100)")

        yield StreamEvent(
            event=StreamEventType.STATUS,
            data=StatusEventData(
                step="guardrail",
                message=f"Query {'is in scope' if guardrail_result.is_in_scope else 'is out of scope'}",
                details={
                    "score": guardrail_result.score,
                    "threshold": self.guardrail_threshold,
                    "reasoning": guardrail_result.reasoning,
                },
            ),
        )

        # Handle out of scope
        if guardrail_result.score < self.guardrail_threshold:
            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="out_of_scope",
                    message="Generating out-of-scope response...",
                ),
            )

            # Generate out-of-scope response with streaming
            system, user = (
                PromptBuilder(OUT_OF_SCOPE_SYSTEM_PROMPT)
                .with_conversation(self.conversation_formatter, history)
                .with_query(query, label="User query")
                .with_note(
                    f"Score: {guardrail_result.score}/100. Reason: {guardrail_result.reasoning}"
                )
                .build()
            )

            answer_chunks: list[str] = []
            response = await self.llm_client.generate_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
                max_tokens=300,
                stream=True,
            )

            if isinstance(response, str):
                answer_chunks.append(response)
                yield StreamEvent(
                    event=StreamEventType.CONTENT,
                    data=ContentEventData(token=response),
                )
            else:
                async for token in response:
                    answer_chunks.append(token)
                    yield StreamEvent(
                        event=StreamEventType.CONTENT,
                        data=ContentEventData(token=token),
                    )

            answer = "".join(answer_chunks)

            # Save turn if session provided
            turn_number = 0
            if session_id and self.conversation_repo:
                turn = await self.conversation_repo.save_turn(
                    session_id,
                    TurnData(
                        user_query=query,
                        agent_response=answer,
                        provider=self.llm_client.provider_name,
                        model=self.llm_client.model,
                        guardrail_score=guardrail_result.score,
                        retrieval_attempts=0,
                        rewritten_query=None,
                        sources=None,
                        reasoning_steps=reasoning_steps,
                    ),
                )
                turn_number = turn.turn_number

            execution_time = (time.time() - start_time) * 1000

            yield StreamEvent(
                event=StreamEventType.METADATA,
                data=MetadataEventData(
                    query=query,
                    execution_time_ms=execution_time,
                    retrieval_attempts=0,
                    rewritten_query=None,
                    guardrail_score=guardrail_result.score,
                    provider=self.llm_client.provider_name,
                    model=self.llm_client.model,
                    session_id=session_id,
                    turn_number=turn_number,
                    reasoning_steps=reasoning_steps,
                ),
            )

            yield StreamEvent(event=StreamEventType.DONE, data={})
            return

        # Step 2: Retrieval loop
        retrieval_attempts = 0
        relevant_chunks: list[dict] = []
        retrieved_chunks: list[dict] = []
        rewritten_query: str | None = None
        current_query = query

        while retrieval_attempts < self.max_retrieval_attempts:
            retrieval_attempts += 1

            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="retrieval",
                    message=f"Searching documents (attempt {retrieval_attempts})...",
                    details={"attempt": retrieval_attempts, "query": current_query[:100]},
                ),
            )

            # Retrieve chunks
            results = await self.search_service.hybrid_search(
                query=current_query, top_k=self.top_k * 2, mode="hybrid"
            )

            retrieved_chunks = [
                {
                    "chunk_id": str(r.chunk_id),
                    "chunk_text": r.chunk_text,
                    "arxiv_id": r.arxiv_id,
                    "title": r.title,
                    "authors": r.authors if hasattr(r, "authors") else [],
                    "section_name": r.section_name,
                    "score": r.score,
                    "pdf_url": (
                        r.pdf_url
                        if hasattr(r, "pdf_url")
                        else f"https://arxiv.org/pdf/{r.arxiv_id}.pdf"
                    ),
                    "published_date": r.published_date if hasattr(r, "published_date") else None,
                }
                for r in results
            ]

            reasoning_steps.append(f"Retrieved documents (attempt {retrieval_attempts})")

            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="grading",
                    message=f"Grading {len(retrieved_chunks)} documents...",
                ),
            )

            # Grade chunks in parallel
            async def grade_single_chunk(chunk: dict) -> GradingResult:
                prompt = get_grading_prompt(current_query, chunk)
                result = await self.llm_client.generate_structured(
                    messages=[{"role": "user", "content": prompt}],
                    response_format=GradingResult,
                )
                result.chunk_id = chunk["chunk_id"]
                return result

            grading_tasks = [grade_single_chunk(chunk) for chunk in retrieved_chunks]
            grading_results = await asyncio.gather(*grading_tasks)

            # Filter relevant chunks
            relevant_chunks = [
                chunk
                for chunk, grade in zip(retrieved_chunks, grading_results)
                if grade.is_relevant
            ]

            relevant_count = len(relevant_chunks)
            total_count = len(retrieved_chunks)
            reasoning_steps.append(f"Graded documents ({relevant_count}/{total_count} relevant)")

            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="grading",
                    message=f"Found {relevant_count} relevant documents",
                    details={"relevant": relevant_count, "total": total_count},
                ),
            )

            # Check if we have enough relevant chunks
            if relevant_count >= self.top_k:
                break

            # Check if we've reached max attempts
            if retrieval_attempts >= self.max_retrieval_attempts:
                reasoning_steps.append("Max attempts reached, proceeding with available documents")
                break

            # Rewrite query
            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="rewrite",
                    message="Rewriting query for better retrieval...",
                ),
            )

            feedback = "\n".join(
                [
                    f"- Chunk from {retrieved_chunks[i]['arxiv_id']}: "
                    f"{'RELEVANT' if g.is_relevant else 'NOT RELEVANT'} - {g.reasoning}"
                    for i, g in enumerate(grading_results[:3])
                ]
            )

            rewrite_prompt = get_rewrite_prompt(query, feedback)
            rewritten_response = await self.llm_client.generate_completion(
                messages=[{"role": "user", "content": rewrite_prompt}], temperature=0.5
            )

            if isinstance(rewritten_response, str):
                rewritten_query = rewritten_response.strip()
            else:
                chunks_list: list[str] = []
                async for chunk in rewritten_response:
                    chunks_list.append(chunk)
                rewritten_query = "".join(chunks_list).strip()

            current_query = rewritten_query
            reasoning_steps.append(f"Rewrote query: '{rewritten_query}'")

            yield StreamEvent(
                event=StreamEventType.STATUS,
                data=StatusEventData(
                    step="rewrite",
                    message="Query rewritten",
                    details={"rewritten_query": rewritten_query},
                ),
            )

        # Step 3: Yield sources
        sources = [
            SourceInfo(
                arxiv_id=chunk["arxiv_id"],
                title=chunk["title"],
                authors=chunk["authors"],
                pdf_url=chunk["pdf_url"],
                relevance_score=chunk["score"],
                published_date=chunk.get("published_date"),
                was_graded_relevant=True,
            )
            for chunk in relevant_chunks[: self.top_k]
        ]

        yield StreamEvent(
            event=StreamEventType.SOURCES,
            data=SourcesEventData(sources=sources),
        )

        # Step 4: Generate answer with streaming
        yield StreamEvent(
            event=StreamEventType.STATUS,
            data=StatusEventData(
                step="generation",
                message="Generating answer...",
            ),
        )

        builder = (
            PromptBuilder(ANSWER_SYSTEM_PROMPT)
            .with_conversation(self.conversation_formatter, history)
            .with_retrieval_context(relevant_chunks[: self.top_k])
            .with_query(query)
        )

        if retrieval_attempts >= self.max_retrieval_attempts and len(relevant_chunks) < self.top_k:
            builder.with_note("Limited sources found. Acknowledge gaps if needed.")

        system_prompt, user_prompt = builder.build()

        answer_chunks: list[str] = []
        response = await self.llm_client.generate_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=1000,
            stream=True,
        )

        if isinstance(response, str):
            answer_chunks.append(response)
            yield StreamEvent(
                event=StreamEventType.CONTENT,
                data=ContentEventData(token=response),
            )
        else:
            async for token in response:
                answer_chunks.append(token)
                yield StreamEvent(
                    event=StreamEventType.CONTENT,
                    data=ContentEventData(token=token),
                )

        answer = "".join(answer_chunks)
        reasoning_steps.append("Generated answer with conversation context")

        # Save turn if session provided
        turn_number = 0
        sources_dicts = [
            {
                "arxiv_id": chunk["arxiv_id"],
                "title": chunk["title"],
                "authors": chunk["authors"],
                "pdf_url": chunk["pdf_url"],
                "relevance_score": chunk["score"],
                "published_date": chunk.get("published_date"),
                "was_graded_relevant": True,
            }
            for chunk in relevant_chunks[: self.top_k]
        ]

        if session_id and self.conversation_repo:
            turn = await self.conversation_repo.save_turn(
                session_id,
                TurnData(
                    user_query=query,
                    agent_response=answer,
                    provider=self.llm_client.provider_name,
                    model=self.llm_client.model,
                    guardrail_score=guardrail_result.score,
                    retrieval_attempts=retrieval_attempts,
                    rewritten_query=rewritten_query,
                    sources=sources_dicts,
                    reasoning_steps=reasoning_steps,
                ),
            )
            turn_number = turn.turn_number

        execution_time = (time.time() - start_time) * 1000

        log.info(
            "streaming query complete",
            session_id=session_id,
            sources=len(sources),
            retrieval_attempts=retrieval_attempts,
            guardrail_score=guardrail_result.score,
            turn_number=turn_number,
            answer_len=len(answer),
            execution_time_ms=execution_time,
        )

        yield StreamEvent(
            event=StreamEventType.METADATA,
            data=MetadataEventData(
                query=query,
                execution_time_ms=execution_time,
                retrieval_attempts=retrieval_attempts,
                rewritten_query=rewritten_query,
                guardrail_score=guardrail_result.score,
                provider=self.llm_client.provider_name,
                model=self.llm_client.model,
                session_id=session_id,
                turn_number=turn_number,
                reasoning_steps=reasoning_steps,
            ),
        )

        yield StreamEvent(event=StreamEventType.DONE, data={})
