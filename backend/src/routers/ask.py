"""Standard RAG and streaming endpoints."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from time import time
import json
from typing import AsyncIterator

from src.schemas.ask import AskRequest, AskResponse, StreamRequest
from src.schemas.common import SourceInfo
from src.dependencies import SearchServiceDep, OpenAIClientDep

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest, search_service: SearchServiceDep, openai_client: OpenAIClientDep
) -> AskResponse:
    """
    Standard RAG: Retrieve + Generate.

    Process:
    1. Hybrid search for top-k chunks
    2. Build RAG prompt with chunks as context
    3. Generate answer with OpenAI
    4. Return answer with sources

    Args:
        request: Question and parameters
        search_service: Injected search service
        openai_client: Injected OpenAI client

    Returns:
        AskResponse with answer and sources
    """
    start_time = time()

    # 1. Retrieve relevant chunks
    search_results = await search_service.hybrid_search(
        query=request.query, top_k=request.top_k, mode=request.search_mode
    )

    # 2. Build RAG prompt
    context_str = "\n\n".join(
        [
            f"[Source {i+1} - {r.arxiv_id}]\n"
            f"Title: {r.title}\n"
            f"Section: {r.section_name or 'N/A'}\n"
            f"Content: {r.chunk_text}"
            for i, r in enumerate(search_results)
        ]
    )

    system_prompt = """You are a research assistant specializing in AI/ML papers.
Answer questions based ONLY on the provided context from research papers.
Cite sources using [arxiv_id] format.
If the context is insufficient to answer the question, say so clearly."""

    user_prompt = f"""Context from research papers:
{context_str}

Question: {request.query}

Provide a detailed, technical answer based on the context above. Cite sources."""

    # 3. Generate answer
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    answer = await openai_client.generate_completion(
        messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=False,
    )

    # 4. Build response with sources
    sources = [
        SourceInfo(
            arxiv_id=r.arxiv_id,
            title=r.title,
            authors=r.authors if hasattr(r, "authors") else [],
            pdf_url=r.pdf_url if hasattr(r, "pdf_url") else f"https://arxiv.org/pdf/{r.arxiv_id}.pdf",
            relevance_score=r.score,
            published_date=r.published_date if hasattr(r, "published_date") else None,
        )
        for r in search_results
    ]

    execution_time = (time() - start_time) * 1000

    return AskResponse(
        query=request.query,
        answer=answer,
        sources=sources,
        chunks_used=len(search_results),
        search_mode=request.search_mode,
        model=request.model,
        execution_time_ms=execution_time,
    )


@router.post("/stream")
async def stream(
    request: StreamRequest, search_service: SearchServiceDep, openai_client: OpenAIClientDep
) -> StreamingResponse:
    """
    Streaming RAG: Stream LLM response for lower latency.

    Response format (Server-Sent Events):
    - First message: metadata (sources, chunks_used)
    - Subsequent messages: text chunks
    - Final message: completion signal

    Args:
        request: Question and parameters
        search_service: Injected search service
        openai_client: Injected OpenAI client

    Returns:
        StreamingResponse with SSE
    """

    async def generate_stream() -> AsyncIterator[str]:
        """Generate SSE stream."""
        # 1. Retrieve (same as standard RAG)
        search_results = await search_service.hybrid_search(
            query=request.query, top_k=request.top_k, mode=request.search_mode
        )

        # 2. Send metadata immediately
        sources = [
            {
                "arxiv_id": r.arxiv_id,
                "title": r.title,
                "relevance_score": r.score,
            }
            for r in search_results
        ]

        metadata = {
            "sources": sources,
            "chunks_used": len(search_results),
            "search_mode": request.search_mode,
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # 3. Build prompt (same as standard RAG)
        context_str = "\n\n".join(
            [f"[Source {i+1} - {r.arxiv_id}]\n{r.chunk_text}" for i, r in enumerate(search_results)]
        )

        system_prompt = "You are a research assistant. Answer based on the provided context."
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {request.query}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 4. Stream generation
        full_answer = ""
        stream_gen = await openai_client.generate_completion(
            messages=messages, model=request.model, temperature=request.temperature, max_tokens=1000, stream=True
        )

        async for chunk in stream_gen:
            full_answer += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # 5. Send completion
        yield f"data: {json.dumps({'answer': full_answer, 'done': True})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
