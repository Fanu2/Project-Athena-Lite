"""
Embedding generation utilities.
Uses nomic-embed-text via Ollama for local embedding generation.
"""

import logging
from typing import List, Optional

import numpy as np

from app.ai.ollama_client import OllamaClient, OllamaError

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768  # nomic-embed-text dimension


class EmbeddingGenerator:
    """
    Generates embeddings for text using Ollama's embedding models.

    Supports:
    - Single text embedding
    - Batch embedding generation
    - Embedding caching
    """

    def __init__(
        self,
        client: OllamaClient,
        model: str = "nomic-embed-text",
        cache_size: int = 1000,
    ):
        self.client = client
        self.model = model
        self.cache: dict[str, List[float]] = {}
        self.cache_order: list[str] = []
        self.cache_size = cache_size

    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if text in self.cache:
            return self.cache[text]

        embedding = self.client.generate_embedding(self.model, text)

        self._add_to_cache(text, embedding)
        return embedding

    def generate_batch(
        self,
        texts: List[str],
        batch_size: int = 10,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in parallel

        Returns:
            List of embedding vectors
        """
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                results.append(self.generate(text))
        return results

    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between -1 and 1
        """
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def _add_to_cache(self, text: str, embedding: List[float]) -> None:
        """Add embedding to cache."""
        if len(self.cache) >= self.cache_size:
            oldest = self.cache_order.pop(0)
            del self.cache[oldest]
        self.cache[text] = embedding
        self.cache_order.append(text)


def cosine_similarity(
    a: List[float],
    b: List[float],
) -> float:
    """Calculate cosine similarity between two vectors."""
    return EmbeddingGenerator._cosine_sim(a, b)

# Note: Using a static method isn't ideal; the generator instance is preferred
# but this is kept for standalone utility usage
