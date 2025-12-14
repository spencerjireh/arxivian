"""Agentic RAG service with LangGraph workflow."""

import asyncio
import uuid
import json
from typing import List, Optional
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from src.schemas.langgraph_state import AgentState, GuardrailScoring, GradingResult
from src.services.openai_client import OpenAIClient
from src.services.search_service import SearchService


class AgenticRAGContext:
    """Context object passed to all LangGraph nodes."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        search_service: SearchService,
        model_name: str = "gpt-4o-mini",
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        temperature: float = 0.3,
    ):
        self.openai_client = openai_client
        self.search_service = search_service
        self.model_name = model_name
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts
        self.temperature = temperature


# Node 1: Guardrail
async def guardrail_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """
    Validate query relevance to AI/ML research.

    Uses OpenAI structured outputs to score query on 0-100 scale.
    """
    query = state["messages"][-1].content
    state["original_query"] = query

    prompt = f"""You are a query relevance validator for an AI/ML research paper database.

Score this query on a scale of 0-100:
- 100: Directly about AI/ML research (models, techniques, theory)
- 75-99: Related to AI/ML (applications, datasets, benchmarks)
- 50-74: Tangentially related (computing, statistics)
- 0-49: Not related to AI/ML

Query: {query}

Provide:
- score: Integer 0-100
- reasoning: Brief explanation (1-2 sentences)
- is_in_scope: Boolean (true if score >= {context.guardrail_threshold})"""

    result = await context.openai_client.generate_structured(
        messages=[{"role": "user", "content": prompt}],
        response_format=GuardrailScoring,
        model=context.model_name,
    )

    state["guardrail_result"] = result
    state["metadata"]["guardrail_score"] = result.score
    state["metadata"]["reasoning_steps"].append(f"Validated query scope (score: {result.score}/100)")

    return state


# Node 2: Retrieve (creates tool call)
async def retrieve_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """
    Create tool call for document retrieval.

    LangGraph's ToolNode will execute the actual retrieval.
    """
    query = state.get("rewritten_query") or state["original_query"]

    tool_call_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "retrieve_chunks",
                "args": {"query": query, "top_k": context.top_k * 2},  # Get extra for grading
                "id": f"call_{uuid.uuid4()}",
            }
        ],
    )

    state["messages"].append(tool_call_message)
    state["retrieval_attempts"] += 1
    state["metadata"]["reasoning_steps"].append(
        f"Retrieved documents (attempt {state['retrieval_attempts']})"
    )

    return state


# Tool definition for retrieval
def create_retrieve_tool(search_service: SearchService):
    """Create retrieval tool with search service injected."""

    @tool
    async def retrieve_chunks(query: str, top_k: int) -> List[dict]:
        """
        Retrieve relevant chunks from database using hybrid search.

        Args:
            query: Search query
            top_k: Number of chunks to retrieve

        Returns:
            List of chunk dictionaries with metadata
        """
        results = await search_service.hybrid_search(query=query, top_k=top_k, mode="hybrid")

        return [
            {
                "chunk_id": str(r.chunk_id),
                "chunk_text": r.chunk_text,
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "authors": r.authors if hasattr(r, "authors") else [],
                "section_name": r.section_name,
                "score": r.score,
                "pdf_url": r.pdf_url if hasattr(r, "pdf_url") else f"https://arxiv.org/pdf/{r.arxiv_id}.pdf",
                "published_date": r.published_date if hasattr(r, "published_date") else None,
            }
            for r in results
        ]

    return retrieve_chunks


# Node 4: Grade Documents
async def grade_documents_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """
    Grade retrieved chunks for relevance to query.

    Uses parallel LLM calls for speed.
    """
    query = state.get("rewritten_query") or state["original_query"]

    # Extract chunks from tool messages
    chunks = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            chunks = json.loads(msg.content)
            break

    state["retrieved_chunks"] = chunks

    # Grade all chunks in parallel
    async def grade_single_chunk(chunk: dict) -> GradingResult:
        prompt = f"""Is this chunk relevant to the query?

Query: {query}

Chunk (from paper {chunk['arxiv_id']}):
{chunk['chunk_text'][:500]}...

Respond with:
- is_relevant: Boolean (true if this chunk helps answer the query)
- reasoning: Brief explanation (1 sentence)"""

        result = await context.openai_client.generate_structured(
            messages=[{"role": "user", "content": prompt}],
            response_format=GradingResult,
            model=context.model_name,
        )
        result.chunk_id = chunk["chunk_id"]
        return result

    grading_tasks = [grade_single_chunk(chunk) for chunk in chunks]
    grading_results = await asyncio.gather(*grading_tasks)

    # Filter relevant chunks
    relevant_chunks = [chunk for chunk, grade in zip(chunks, grading_results) if grade.is_relevant]

    state["grading_results"] = grading_results
    state["relevant_chunks"] = relevant_chunks

    relevant_count = len(relevant_chunks)
    total_count = len(chunks)
    state["metadata"]["reasoning_steps"].append(
        f"Graded documents ({relevant_count}/{total_count} relevant)"
    )

    # Routing decision
    if relevant_count >= context.top_k:
        state["routing_decision"] = "generate_answer"
    elif state["retrieval_attempts"] >= context.max_retrieval_attempts:
        state["routing_decision"] = "generate_answer"  # Use what we have
        state["metadata"]["reasoning_steps"].append("Max attempts reached, proceeding with available documents")
    else:
        state["routing_decision"] = "rewrite_query"

    return state


# Node 5: Rewrite Query
async def rewrite_query_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """Rewrite query based on grading feedback for better retrieval."""
    original_query = state["original_query"]
    grading_results = state["grading_results"]

    feedback = "\n".join(
        [
            f"- Chunk from {state['retrieved_chunks'][i]['arxiv_id']}: "
            f"{'RELEVANT' if g.is_relevant else 'NOT RELEVANT'} - {g.reasoning}"
            for i, g in enumerate(grading_results[:3])
        ]
    )

    prompt = f"""The original query did not retrieve enough relevant documents.

Original Query: {original_query}

Retrieval Feedback:
{feedback}

Rewrite the query to improve retrieval. Focus on:
- Technical terminology used in research papers
- Specific AI/ML concepts
- Key terms that would appear in relevant papers

Return ONLY the rewritten query, no explanation."""

    rewritten = await context.openai_client.generate_completion(
        messages=[{"role": "user", "content": prompt}], model=context.model_name, temperature=0.5
    )

    state["rewritten_query"] = rewritten.strip()
    state["metadata"]["reasoning_steps"].append(f"Rewrote query: '{rewritten.strip()}'")

    return state


# Node 6: Generate Answer
async def generate_answer_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """Generate final answer from relevant chunks."""
    query = state["original_query"]
    chunks = state["relevant_chunks"][: context.top_k]

    context_str = "\n\n".join(
        [
            f"[Source {i+1} - {c['arxiv_id']}]\n"
            f"Title: {c['title']}\n"
            f"Section: {c.get('section_name', 'N/A')}\n"
            f"Content: {c['chunk_text']}"
            for i, c in enumerate(chunks)
        ]
    )

    system_prompt = """You are a research assistant specializing in AI/ML papers.
Answer questions based ONLY on the provided context from research papers.
Cite sources using [arxiv_id] format.
Be precise, technical, and thorough."""

    user_prompt = f"""Context from research papers:
{context_str}

Question: {query}

Provide a detailed answer based on the context above. Cite sources."""

    answer = await context.openai_client.generate_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=context.model_name,
        temperature=context.temperature,
        max_tokens=1000,
        stream=False,
    )

    state["messages"].append(AIMessage(content=answer))
    state["metadata"]["reasoning_steps"].append("Generated answer from context")

    return state


# Out of scope handler
async def out_of_scope_node(state: AgentState, context: AgenticRAGContext) -> dict:
    """Handle out-of-scope queries."""
    guardrail_result = state["guardrail_result"]

    message = f"""I'm sorry, but this query doesn't appear to be related to AI/ML research.

Your query: {state['original_query']}

Relevance score: {guardrail_result.score}/100
Reasoning: {guardrail_result.reasoning}

I can only answer questions about artificial intelligence and machine learning research papers.
Please try rephrasing your question to focus on AI/ML topics."""

    state["messages"].append(AIMessage(content=message))
    return state


# Conditional edge functions
def continue_after_guardrail(state: AgentState) -> str:
    """Route based on guardrail score."""
    score = state["guardrail_result"].score
    threshold = state["metadata"].get("guardrail_threshold", 75)

    if score >= threshold:
        return "continue"
    else:
        return "out_of_scope"


def continue_after_grading(state: AgentState) -> str:
    """Route based on grading results."""
    return state["routing_decision"]


# Graph building function
def build_agentic_rag_graph(
    openai_client: OpenAIClient,
    search_service: SearchService,
    model_name: str = "gpt-4o-mini",
    guardrail_threshold: int = 75,
    top_k: int = 3,
    max_retrieval_attempts: int = 3,
    temperature: float = 0.3,
):
    """
    Build and compile the agentic RAG workflow graph.

    Returns:
        Compiled LangGraph workflow
    """
    # Create context
    context = AgenticRAGContext(
        openai_client=openai_client,
        search_service=search_service,
        model_name=model_name,
        guardrail_threshold=guardrail_threshold,
        top_k=top_k,
        max_retrieval_attempts=max_retrieval_attempts,
        temperature=temperature,
    )

    # Create workflow
    workflow = StateGraph(AgentState)

    # Create tools
    retrieve_tool = create_retrieve_tool(search_service)
    tool_node = ToolNode([retrieve_tool])

    # Add nodes (with context binding)
    workflow.add_node("guardrail", lambda s: guardrail_node(s, context))
    workflow.add_node("out_of_scope", lambda s: out_of_scope_node(s, context))
    workflow.add_node("retrieve", lambda s: retrieve_node(s, context))
    workflow.add_node("tool_retrieve", tool_node)
    workflow.add_node("grade_documents", lambda s: grade_documents_node(s, context))
    workflow.add_node("rewrite_query", lambda s: rewrite_query_node(s, context))
    workflow.add_node("generate_answer", lambda s: generate_answer_node(s, context))

    # Add edges
    workflow.add_edge(START, "guardrail")

    workflow.add_conditional_edges(
        "guardrail", continue_after_guardrail, {"continue": "retrieve", "out_of_scope": "out_of_scope"}
    )

    workflow.add_edge("out_of_scope", END)

    # After retrieve, always go to tool_retrieve
    workflow.add_edge("retrieve", "tool_retrieve")

    # After tool_retrieve, always grade
    workflow.add_edge("tool_retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        continue_after_grading,
        {"generate_answer": "generate_answer", "rewrite_query": "rewrite_query"},
    )

    # After rewrite, go back to retrieve
    workflow.add_edge("rewrite_query", "retrieve")

    # After generate_answer, done
    workflow.add_edge("generate_answer", END)

    # Compile
    return workflow.compile()


class AgenticRAGService:
    """
    Service for executing agentic RAG workflows.

    Wraps LangGraph workflow with a clean interface.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        search_service: SearchService,
        model_name: str = "gpt-4o-mini",
        guardrail_threshold: int = 75,
        top_k: int = 3,
        max_retrieval_attempts: int = 3,
        temperature: float = 0.3,
    ):
        self.graph = build_agentic_rag_graph(
            openai_client=openai_client,
            search_service=search_service,
            model_name=model_name,
            guardrail_threshold=guardrail_threshold,
            top_k=top_k,
            max_retrieval_attempts=max_retrieval_attempts,
            temperature=temperature,
        )
        self.model_name = model_name
        self.guardrail_threshold = guardrail_threshold
        self.top_k = top_k
        self.max_retrieval_attempts = max_retrieval_attempts

    async def ask(self, query: str) -> dict:
        """
        Execute agentic RAG workflow.

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
        }
