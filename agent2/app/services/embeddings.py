"""
app/services/embeddings.py

Generates sentence embeddings using sentence-transformers (all-MiniLM-L6-v2).
Model is loaded once at class instantiation and reused across all calls.

No database. No network calls after model load.
"""

from typing import Optional

import numpy as np
from loguru import logger

# Model name — change here to swap models project-wide
_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    """
    Generates dense vector embeddings for text using sentence-transformers.

    The model is loaded once when the class is instantiated.
    Pass the same instance to avoid reloading on every call.

    Usage:
        embedder = EmbeddingService()
        vector = embedder.embed("Lost ₹50,000 to a fake investment app")
        vectors = embedder.embed_many(["text one", "text two"])
    """

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence_transformers is required for EmbeddingService. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        logger.info("EmbeddingService: loading model '{}'...", _MODEL_NAME)
        self.model = SentenceTransformer(_MODEL_NAME)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.success(
            "EmbeddingService: model loaded. Embedding dimension: {}.", self.dimension
        )

    def embed(self, text: str) -> Optional[list[float]]:
        """
        Generate an embedding for a single text string.

        Returns:
            list[float] of length `self.dimension`, or None on failure.
        """
        if not text or not text.strip():
            logger.debug("EmbeddingService.embed: skipping empty text.")
            return None

        try:
            raw_vector = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,   # unit norm — required for cosine similarity
            )
            vector = np.asarray(raw_vector)
            return vector.tolist()

        except Exception as e:
            logger.error("EmbeddingService.embed failed: {}", e)
            return None

    def embed_many(self, texts: list[str]) -> list[Optional[list[float]]]:
        """
        Generate embeddings for a batch of texts efficiently.

        Returns a list parallel to `texts`.
        Texts that are empty will have None in their position.
        """
        if not texts:
            return []

        # Separate valid from empty inputs to keep batch efficient
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts   = [texts[i] for i in valid_indices]

        results: list[Optional[list[float]]] = [None] * len(texts)

        if not valid_texts:
            return results

        try:
            raw_vectors = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=64,
                show_progress_bar=False,
            )
            vectors = np.asarray(raw_vectors)

            for idx, vector in zip(valid_indices, vectors):
                results[idx] = vector.tolist()

            logger.debug(
                "EmbeddingService.embed_many: embedded {}/{} texts.",
                len(valid_texts), len(texts),
            )

        except Exception as e:
            logger.error("EmbeddingService.embed_many failed: {}", e)

        return results
