"""Prompt templates for agent workflow."""


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

Chunk (from paper {chunk['arxiv_id']}):
{chunk['chunk_text'][:500]}...

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


def get_out_of_scope_message(query: str, score: int, reasoning: str) -> str:
    """
    Generate out-of-scope rejection message.

    Args:
        query: User's query
        score: Guardrail score
        reasoning: Guardrail reasoning

    Returns:
        Formatted rejection message
    """
    return f"""I'm sorry, but this query doesn't appear to be related to AI/ML research.

Your query: {query}

Relevance score: {score}/100
Reasoning: {reasoning}

I can only answer questions about artificial intelligence and machine learning research papers.
Please try rephrasing your question to focus on AI/ML topics."""
