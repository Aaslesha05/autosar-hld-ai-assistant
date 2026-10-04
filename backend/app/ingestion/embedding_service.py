"""
embedding_service.py
--------------------
Configurable Sentence Transformers embedding service.

Features:
- Singleton / cached model loading (loads once per process, never per chunk)
- Batch embedding generation with configurable batch sizes
- Safe handling of empty, whitespace, or invalid texts
- Pre-normalized embeddings for fast cosine similarity
- Clean configuration exposure without calling LLMs
"""

import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger("autosar_hld_embeddings")

class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self._ensure_model_loaded()

    def _ensure_model_loaded(self) -> None:
        """Load SentenceTransformer model once and cache it."""
        if EmbeddingService._model is None:
            logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
            try:
                EmbeddingService._model = SentenceTransformer(self.model_name)
                if hasattr(EmbeddingService._model, "get_embedding_dimension"):
                    dim = EmbeddingService._model.get_embedding_dimension()
                else:
                    dim = EmbeddingService._model.get_sentence_embedding_dimension()
                logger.info(f"SentenceTransformer '{self.model_name}' loaded successfully. Dimension: {dim}")
            except Exception as e:
                logger.error(f"Failed to load embedding model '{self.model_name}': {e}", exc_info=True)
                raise RuntimeError(f"Embedding model initialization failed: {str(e)}")

    @property
    def model(self) -> SentenceTransformer:
        if EmbeddingService._model is None:
            self._ensure_model_loaded()
        return EmbeddingService._model

    @property
    def dimension(self) -> int:
        """Return sentence embedding vector dimension (e.g. 384 for all-MiniLM-L6-v2)."""
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """
        Generate normalized vector embeddings for a list of text strings in batches.
        Safely replaces empty/invalid strings with fallback to prevent shape errors.
        """
        if not texts:
            return []

        bs = batch_size or self.batch_size
        safe_texts = []
        for t in texts:
            clean = str(t).strip() if t is not None else ""
            # Prevent empty text error in transformers by providing fallback
            safe_texts.append(clean if clean else "[EMPTY_CHUNK]")

        try:
            embeddings_np = self.model.encode(
                safe_texts,
                batch_size=bs,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            return embeddings_np.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings for {len(texts)} texts: {e}", exc_info=True)
            raise RuntimeError(f"Embedding generation failed: {str(e)}")

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a single search/retrieval query string."""
        clean_query = str(query).strip() if query else "[EMPTY_QUERY]"
        emb = self.model.encode(
            clean_query,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return emb.tolist()


def get_embedding_service() -> EmbeddingService:
    """Singleton getter for the project embedding service."""
    if EmbeddingService._instance is None:
        EmbeddingService._instance = EmbeddingService()
    return EmbeddingService._instance
