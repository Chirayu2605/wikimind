"""
embeddings.py — Sentence-transformer embedding wrapper.

The model is loaded ONCE at module import time (not per-request).
This is critical: loading the model takes ~1-2 seconds and several hundred MB;
doing it on every request would make the API unusably slow.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

# Module-level singleton — loaded once when the worker starts
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """
    Embed a list of strings and return a 2-D NumPy array of shape (N, 384).

    Calling this with a single string is a common mistake — wrap it in a list.
    """
    if not texts:
        return np.empty((0, 384), dtype=np.float32)
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.astype(np.float32)
