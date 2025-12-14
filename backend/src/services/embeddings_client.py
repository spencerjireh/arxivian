"""Jina AI embeddings client."""

from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class JinaEmbeddingsClient:
    """Client for Jina AI embeddings API."""

    def __init__(self, api_key: str, model: str = "jina-embeddings-v3"):
        """
        Initialize Jina embeddings client.

        Args:
            api_key: Jina API key
            model: Model name (default: jina-embeddings-v3)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.jina.ai/v1/embeddings"
        self.dimension = 1024  # Jina v3 outputs 1024-dim embeddings

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            1024-dimensional embedding vector
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "task": "retrieval.query",
                    "input": [query],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.

        Args:
            texts: List of document texts

        Returns:
            List of 1024-dimensional embedding vectors
        """
        # Batch processing (Jina supports up to 100 texts per request)
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "task": "retrieval.passage",
                        "input": batch,
                    },
                )
                response.raise_for_status()
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(embeddings)

        return all_embeddings
