"""Agent service with LangGraph workflow."""

from langchain_core.messages import HumanMessage

from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.conversation import ConversationMessage, TurnData
from src.utils.logger import get_logger
from .graph_builder import build_agent_graph

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
        self.conversation_repo = conversation_repo
        self.conversation_window = conversation_window
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts

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
