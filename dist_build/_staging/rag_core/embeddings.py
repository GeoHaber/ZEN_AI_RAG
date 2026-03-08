"""
rag_core.embeddings — Embedding Model Manager
================================================

Handles loading, fallback, and caching of embedding models.
Supports code-specific models (GraphCodeBERT) and general models (MiniLM).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model registry — best → fastest
# ---------------------------------------------------------------------------

EMBEDDING_MODELS: List[Tuple[str, str, int]] = [
    # Code-specific (best for code/function similarity)
    ("microsoft/graphcodebert-base", "code", 768),
    ("microsoft/codebert-base", "code", 768),
    # General purpose (best for natural language documents)
    ("all-MiniLM-L6-v2", "general", 384),
    ("paraphrase-MiniLM-L6-v2", "general", 384),
    ("paraphrase-multilingual-MiniLM-L12-v2", "multilingual", 384),
]

# Cache dir for downloaded models
_DEFAULT_CACHE = Path.home() / ".cache" / "rag_core" / "models"


class EmbeddingManager:
    """
    Manages loading and inference of embedding models.

    Features:
    - Priority-ordered model hierarchy with automatic fallback
    - GPU acceleration with FP16 when available
    - Batch encoding with progress callbacks
    - Normalised embeddings for cosine similarity via dot product
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        prefer_code: bool = False,
        device: Optional[str] = None,
        use_fp16: bool = True,
    ):
        self.model_name = model_name
        self.prefer_code = prefer_code
        self._device = device
        self._use_fp16 = use_fp16
        self._model = None
        self._model_type: str = "none"
        self._dim: int = 0

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_type(self) -> str:
        return self._model_type

    @property
    def dimension(self) -> int:
        return self._dim

    def load(self) -> bool:
        """Load the best available embedding model.

        Returns True if a model was loaded, False if no model available.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.warning("sentence-transformers not installed")
            return False

        models_to_try = []
        if self.model_name:
            models_to_try.append((self.model_name, "custom", 768))
        if self.prefer_code:
            models_to_try.extend(EMBEDDING_MODELS)
        else:
            # Put general models first
            models_to_try.extend(
                [m for m in EMBEDDING_MODELS if m[1] != "code"] + [m for m in EMBEDDING_MODELS if m[1] == "code"]
            )

        for name, mtype, dim in models_to_try:
            try:
                logger.info("Loading embedding model: %s (%s)", name, mtype)
                device = self._device
                if device is None:
                    import torch

                    device = "cuda" if torch.cuda.is_available() else "cpu"

                model = SentenceTransformer(name, device=device)

                # Enable FP16 on GPU
                if self._use_fp16 and device == "cuda":
                    model = model.half()

                self._model = model
                self._model_type = mtype
                self._dim = model.get_sentence_embedding_dimension()
                logger.info(
                    "Loaded %s — dim=%d, type=%s, device=%s",
                    name,
                    self._dim,
                    mtype,
                    device,
                )
                return True
            except Exception as e:
                logger.debug("Failed to load %s: %s", name, e)

        return False

    def encode(
        self,
        texts: List[str],
        *,
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode texts into embeddings.

        Args:
            texts: List of texts to encode.
            batch_size: Batch size for encoding.
            normalize: Whether to L2-normalise (enables dot-product = cosine).
            show_progress: Show tqdm progress bar.

        Returns:
            numpy array of shape (len(texts), dim).
        """
        if self._model is None:
            raise RuntimeError("No embedding model loaded. Call load() first.")

        return self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
        )

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """Encode a single text into an embedding vector."""
        return self.encode([text], normalize=normalize)[0]

    def cosine_similarity(self, query_vec: np.ndarray, corpus_vecs: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and corpus.

        Assumes vectors are L2-normalised (dot product = cosine).
        """
        return corpus_vecs @ query_vec

    def save_embeddings(self, embeddings: np.ndarray, path: Path) -> None:
        """Save embeddings to disk for persistent caching."""
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(path), embeddings)
        logger.info("Saved embeddings to %s (%s)", path, embeddings.shape)

    def load_embeddings(self, path: Path) -> Optional[np.ndarray]:
        """Load cached embeddings from disk."""
        if not path.exists():
            return None
        try:
            emb = np.load(str(path))
            logger.info("Loaded embeddings from %s (%s)", path, emb.shape)
            return emb
        except Exception as e:
            logger.warning("Failed to load embeddings from %s: %s", path, e)
            return None
