"""Prompt templates for agent workflow."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.schemas.conversation import ConversationMessage
    from .context import ConversationFormatter


# System prompt constants
ANSWER_SYSTEM_PROMPT = """You are a research assistant specializing in AI/ML papers.
Answer based ONLY on provided context. Cite sources as [arxiv_id].
Be precise, technical, and conversational. Avoid robotic phrases."""

OUT_OF_SCOPE_SYSTEM_PROMPT = """You are an AI/ML research assistant.
The user's query is outside your scope. Respond helpfully:
- Explain you specialize in AI/ML research papers
- Suggest how they might rephrase for AI/ML relevance
- Be concise (2-3 sentences), professional, not over-apologetic"""

ROUTER_SYSTEM_PROMPT = """You are a routing agent for an AI/ML research assistant.
Your job is to decide the next action based on the conversation and available tools.

Available tools:
{tool_descriptions}

Guidelines:
1. Use retrieve_chunks when you need information from research papers
2. Use web_search for recent information (2024+) or current events
3. Choose "generate" when you have enough context to answer the user's question
4. Consider the conversation history - avoid redundant tool calls
5. If previous retrieval found relevant documents, you likely have enough context

Decision criteria:
- New query about AI/ML concepts -> retrieve_chunks
- Question about recent developments -> web_search
- Follow-up on retrieved context -> likely generate
- Query already has sufficient context from tool_history -> generate"""


class PromptBuilder:
    """Composable prompt builder for LLM calls."""

    def __init__(self, system_base: str):
        self._system = system_base
        self._user_parts: list[str] = []

    def with_conversation(
        self,
        formatter: ConversationFormatter,
        history: list[ConversationMessage],
    ) -> PromptBuilder:
        """Add conversation history to the prompt."""
        formatted = formatter.format_for_prompt(history)
        if formatted:
            self._user_parts.append(formatted)
        return self

    def with_retrieval_context(self, chunks: list[dict]) -> PromptBuilder:
        """Add retrieval context from chunks."""
        if chunks:
            context_parts = []
            for i, c in enumerate(chunks):
                context_parts.append(
                    f"[Source {i + 1} - {c['arxiv_id']}]\n"
                    f"Title: {c['title']}\n"
                    f"Section: {c.get('section_name', 'N/A')}\n"
                    f"Content: {c['chunk_text']}"
                )
            context = "\n\n".join(context_parts)
            self._user_parts.append(f"Retrieved context:\n{context}")
        return self

    def with_query(self, query: str, label: str = "Question") -> PromptBuilder:
        """Add the user's query."""
        self._user_parts.append(f"{label}: {query}")
        return self

    def with_note(self, note: str) -> PromptBuilder:
        """Add a note to the prompt."""
        self._user_parts.append(f"Note: {note}")
        return self

    def build(self) -> tuple[str, str]:
        """Build the final system and user prompts."""
        return self._system, "\n\n".join(self._user_parts)


def get_guardrail_prompt(query: str, threshold: int) -> str:
    """
    Generate guardrail validation prompt.

    Args:
        query: User's query to validate
        threshold: Minimum acceptable score

    Returns:
        Formatted prompt for guardrail validation
    """
    return f"""You are a query relevance validator for an AI/ML research paper database.

Score this query on a scale of 0-100:
- 100: Directly about AI/ML research (models, techniques, theory)
- 75-99: Related to AI/ML (applications, datasets, benchmarks)
- 50-74: Tangentially related (computing, statistics)
- 0-49: Not related to AI/ML

Query: {query}

Provide:
- score: Integer 0-100
- reasoning: Brief explanation (1-2 sentences)
- is_in_scope: Boolean (true if score >= {threshold})"""


def get_grading_prompt(query: str, chunk: dict) -> str:
    """
    Generate chunk grading prompt.

    Args:
        query: User's query
        chunk: Chunk dictionary with metadata

    Returns:
        Formatted prompt for chunk relevance grading
    """
    return f"""Is this chunk relevant to the query?

Query: {query}

Chunk (from paper {chunk["arxiv_id"]}):
{chunk["chunk_text"][:500]}...

Respond with:
- is_relevant: Boolean (true if this chunk helps answer the query)
- reasoning: Brief explanation (1 sentence)"""


def get_rewrite_prompt(original_query: str, feedback: str) -> str:
    """
    Generate query rewrite prompt.

    Args:
        original_query: User's original query
        feedback: Feedback from grading results

    Returns:
        Formatted prompt for query rewriting
    """
    return f"""The original query did not retrieve enough relevant documents.

Original Query: {original_query}

Retrieval Feedback:
{feedback}

Rewrite the query to improve retrieval. Focus on:
- Technical terminology used in research papers
- Specific AI/ML concepts
- Key terms that would appear in relevant papers

Return ONLY the rewritten query, no explanation."""


def get_answer_generation_prompts(query: str, context_str: str) -> tuple[str, str]:
    """
    Generate system and user prompts for answer generation.

    Args:
        query: User's original query
        context_str: Formatted context from relevant chunks

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are a research assistant specializing in AI/ML papers.
Answer questions based ONLY on the provided context from research papers.
Cite sources using [arxiv_id] format.
Be precise, technical, and thorough."""

    user_prompt = f"""Context from research papers:
{context_str}

Question: {query}

Provide a detailed answer based on the context above. Cite sources."""

    return system_prompt, user_prompt


def get_router_prompt(
    query: str,
    tool_schemas: list[dict],
    tool_history: list[dict] | None = None,
    conversation_context: str = "",
) -> tuple[str, str]:
    """
    Generate router prompt for tool selection.

    Args:
        query: User's current query
        tool_schemas: List of tool schemas with name and description
        tool_history: Previous tool executions in this session
        conversation_context: Formatted conversation history

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format tool descriptions
    tool_desc_lines = []
    for schema in tool_schemas:
        tool_desc_lines.append(f"- {schema['name']}: {schema['description']}")
    tool_descriptions = "\n".join(tool_desc_lines)

    system_prompt = ROUTER_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

    # Build user prompt
    user_parts = []

    if conversation_context:
        user_parts.append(f"Conversation history:\n{conversation_context}")

    if tool_history:
        history_lines = ["Previous tool calls in this turn:"]
        for exec_info in tool_history:
            status = "success" if exec_info.get("success") else "failed"
            history_lines.append(
                f"- {exec_info['tool_name']}: {status} - {exec_info.get('result_summary', 'no summary')}"
            )
        user_parts.append("\n".join(history_lines))

    user_parts.append(f"Current query: {query}")
    user_parts.append(
        "Decide: Should you call a tool (and which one with what arguments), or generate a response?"
    )

    user_prompt = "\n\n".join(user_parts)

    return system_prompt, user_prompt
