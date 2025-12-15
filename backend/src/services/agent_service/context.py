"""Context object passed to all LangGraph nodes."""

from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService


class AgentContext:
    """Context object passed to all LangGraph nodes."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.search_service = search_service
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.temperature = temperature
