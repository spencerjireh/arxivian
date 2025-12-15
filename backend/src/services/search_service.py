"""Hybrid search service with RRF fusion."""

from typing import List
from collections import defaultdict
from src.repositories.search_repository import SearchRepository, SearchResult
from src.clients.embeddings_client import JinaEmbeddingsClient


class SearchService:
    """Service for hybrid search with Reciprocal Rank Fusion."""

    def __init__(
        self,
        search_repository: SearchRepository,
        embeddings_client: JinaEmbeddingsClient,
        rrf_k: int = 60,
    ):
        """
        Initialize search service.

        Args:
            search_repository: Repository for search operations
            embeddings_client: Client for generating embeddings
            rrf_k: RRF constant (default 60 from research)
        """
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

        Returns:
            List of SearchResult objects ranked by relevance
        """
        if mode == "vector":
            return await self._vector_only_search(query, top_k, min_score)
        elif mode == "fulltext":
            return await self._fulltext_only_search(query, top_k)
        else:  # hybrid
            return await self._hybrid_search_rrf(query, top_k, min_score)

    async def _vector_only_search(
        self, query: str, top_k: int, min_score: float
    ) -> List[SearchResult]:
        """Vector similarity search only."""
        # Generate query embedding
        query_embedding = await self.embeddings_client.embed_query(query)

        # Search
        results = await self.search_repo.vector_search(
            query_embedding=query_embedding, top_k=top_k, min_score=min_score
        )

        return results

    async def _fulltext_only_search(self, query: str, top_k: int) -> List[SearchResult]:
        """Full-text search only."""
        results = await self.search_repo.fulltext_search(query=query, top_k=top_k)

        return results

    async def _hybrid_search_rrf(
        self, query: str, top_k: int, min_score: float
    ) -> List[SearchResult]:
        """
        Hybrid search using Reciprocal Rank Fusion.

        Process:
        1. Get top 2*k results from vector search
        2. Get top 2*k results from full-text search
        3. Apply RRF: score = Σ(1 / (rank + k))
        4. Return top k by combined score
        """
        # Get more results than needed for better fusion
        fetch_k = top_k * 2

        # Run both searches in parallel (could use asyncio.gather)
        query_embedding = await self.embeddings_client.embed_query(query)

        vector_results = await self.search_repo.vector_search(
            query_embedding=query_embedding, top_k=fetch_k, min_score=min_score
        )

        fulltext_results = await self.search_repo.fulltext_search(query=query, top_k=fetch_k)

        # Apply RRF fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results=vector_results, fulltext_results=fulltext_results, top_k=top_k
        )

        return fused_results

    def _reciprocal_rank_fusion(
        self, vector_results: List[SearchResult], fulltext_results: List[SearchResult], top_k: int
    ) -> List[SearchResult]:
        """
        Apply Reciprocal Rank Fusion to combine rankings.

        RRF score = Σ (1 / (rank + k))
        where k = 60 is standard from research
        """
        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        all_results = {}  # chunk_id -> SearchResult

        # Add vector search scores
        for rank, result in enumerate(vector_results):
            rrf_scores[result.chunk_id] += 1.0 / (rank + self.rrf_k)
            all_results[result.chunk_id] = result

        # Add fulltext search scores
        for rank, result in enumerate(fulltext_results):
            rrf_scores[result.chunk_id] += 1.0 / (rank + self.rrf_k)
            if result.chunk_id not in all_results:
                all_results[result.chunk_id] = result

        # Sort by RRF score and take top_k
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[
            :top_k
        ]

        # Build final results with RRF scores
        final_results = []
        for chunk_id in sorted_chunk_ids:
            result = all_results[chunk_id]
            # Update score to RRF score (normalized to 0-1)
            result.score = rrf_scores[chunk_id] / (2.0 / self.rrf_k)  # Normalize
            final_results.append(result)

        return final_results
