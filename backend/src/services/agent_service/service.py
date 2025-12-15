"""Agent service with LangGraph workflow."""

from langchain_core.messages import HumanMessage

from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from .graph_builder import build_agent_graph


class AgentService:
    """
    Service for executing agent workflows.

    Wraps LangGraph workflow with a clean interface.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
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
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts

    async def ask(self, query: str) -> dict:
        """
        Execute agent workflow.

        Args:
            query: User question

        Returns:
            Dict with answer, sources, reasoning steps, etc.
        """
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
                "was_graded_relevant": True,  # All in relevant_chunks were graded relevant
            }
            for chunk in result["relevant_chunks"][: self.top_k]
        ]

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "reasoning_steps": result["metadata"]["reasoning_steps"],
            "retrieval_attempts": result["retrieval_attempts"],
            "rewritten_query": result.get("rewritten_query"),
            "guardrail_score": result["guardrail_result"].score if result["guardrail_result"] else None,
            "provider": self.llm_client.provider_name,
            "model": self.llm_client.model,
        }
