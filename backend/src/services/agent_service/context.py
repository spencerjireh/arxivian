"""Context object passed to all LangGraph nodes."""

from src.clients.base_llm_client import BaseLLMClient
from src.services.search_service import SearchService
from src.schemas.conversation import ConversationMessage


class ConversationFormatter:
    """Formats conversation history for prompt injection."""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns

    def format_for_prompt(self, history: list[ConversationMessage]) -> str:
        """
        Format recent history as prompt-ready string.

        Args:
            history: List of conversation messages

        Returns:
            Formatted string for prompt injection
        """
        recent = history[-(self.max_turns * 2) :]  # Last N turns (each turn = 2 messages)
        if not recent:
            return ""

        lines = ["Previous conversation:"]
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            # Truncate long messages to avoid prompt bloat
            content = msg["content"][:500]
            if len(msg["content"]) > 500:
                content += "..."
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def as_messages(self, history: list[ConversationMessage]) -> list[dict]:
        """
        Return history as LLM message format.

        Args:
            history: List of conversation messages

        Returns:
            List of message dicts with role and content
        """
        return [{"role": m["role"], "content": m["content"]} for m in history]


class AgentContext:
    """Context object passed to all LangGraph nodes."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        search_service: SearchService,
        conversation_formatter: ConversationFormatter | None = None,
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.search_service = search_service
        self.conversation_formatter = conversation_formatter or ConversationFormatter()
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.temperature = temperature
