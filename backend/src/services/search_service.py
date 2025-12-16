"""Hybrid search service with RRF fusion."""

from typing import List
from collections import defaultdict
from src.repositories.search_repository import SearchRepository, SearchResult
from src.clients.embeddings_client import JinaEmbeddingsClient
from src.utils.logger import get_logger

log = get_logger(__name__)


class SearchService:
    """Service for hybrid search with Reciprocal Rank Fusion."""

    def __init__(
        self,
        search_repository: SearchRepository,
        embeddings_client: JinaEmbeddingsClient,
        rrf_k: int = 60,
    ):
        self.search_repo = search_repository
        self.embeddings_client = embeddings_client
        self.rrf_k = rrf_k

    async def hybrid_search(
        self, query: str, top_k: int = 10, mode: str = "hybrid", min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Perform hybrid search with vector + full-text + RRF.

        Args:
            query: Search query
            top_k: Number of results to return
            mode: "vector", "fulltext", or "hybrid"
            min_score: Minimum similarity score
        """
        log.info("search started", query=query[:100], mode=mode, top_k=top_k)

        if mode == "vector":
            results = await self._vector_only_search(query, top_k, min_score)
        elif mode == "fulltext":
            results = await self._fulltext_only_search(query, top_k)
        else:
            results = await self._hybrid_search_rrf(query, top_k, min_score)

        log.info("search complete", mode=mode, results=len(results))
        return results

    async def _vector_only_search(
        self, query: str, top_k: int, min_score: float
    ) -> List[SearchResult]:
        """Vector similarity search only."""
        query_embedding = await self.embeddings_client.embed_query(query)
        log.debug("query embedded", embedding_dim=len(query_embedding))

        results = await self.search_repo.vector_search(
            query_embedding=query_embedding, top_k=top_k, min_score=min_score
        )
        log.debug("vector search done", results=len(results))
        return results

    async def _fulltext_only_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Full-text search only."""
        results = await self.search_repo.fulltext_search(query=query, top_k=top_k)
        log.debug("fulltext search done", results=len(results))
        return results

    async def _hybrid_search_rrf(
        self, query: str, top_k: int, min_score: float
    ) -> List[SearchResult]:
        """
        Hybrid search using Reciprocal Rank Fusion.

        Process:
        1. Get top 2*k results from vector search
        2. Get top 2*k results from full-text search
        3. Apply RRF: score = sum(1 / (rank + k))
        4. Return top k by combined score
        """
        fetch_k = top_k * 2

        query_embedding = await self.embeddings_client.embed_query(query)
        log.debug("query embedded", embedding_dim=len(query_embedding))

        vector_results = await self.search_repo.vector_search(
            query_embedding=query_embedding, top_k=fetch_k, min_score=min_score
        )

        fulltext_results = await self.search_repo.fulltext_search(query=query, top_k=fetch_k)

        log.debug(
            "raw search results",
            vector_count=len(vector_results),
            fulltext_count=len(fulltext_results),
        )

        fused_results = self._reciprocal_rank_fusion(
            vector_results=vector_results, fulltext_results=fulltext_results, top_k=top_k
        )

        log.debug("rrf fusion complete", fused_count=len(fused_results))
        return fused_results

    def _reciprocal_rank_fusion(
        self, vector_results: List[SearchResult], fulltext_results: List[SearchResult], top_k: int
    ) -> List[SearchResult]:
        """
        Apply Reciprocal Rank Fusion to combine rankings.

        RRF score = sum(1 / (rank + k)) where k = 60 is standard from research
        """
        rrf_scores = defaultdict(float)
        all_results = {}

        for rank, result in enumerate(vector_results):
            rrf_scores[result.chunk_id] += 1.0 / (rank + self.rrf_k)
            all_results[result.chunk_id] = result

        for rank, result in enumerate(fulltext_results):
            rrf_scores[result.chunk_id] += 1.0 / (rank + self.rrf_k)
            if result.chunk_id not in all_results:
                all_results[result.chunk_id] = result

        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[
            :top_k
        ]

        final_results = []
        for chunk_id in sorted_chunk_ids:
            result = all_results[chunk_id]
            result.score = rrf_scores[chunk_id] / (2.0 / self.rrf_k)
            final_results.append(result)

        return final_results
