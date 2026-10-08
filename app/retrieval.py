"""
retrieval.py — Cosine-similarity-based chunk retrieval.

Manual NumPy implementation — no sklearn, no vector DB.
This is intentional: it keeps the mechanism fully visible and
is perfectly adequate for single-page retrieval at this scale.
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a single query vector and every row of `matrix`.

    Args:
        query_vec: shape (D,)
        matrix:    shape (N, D)

    Returns:
        similarities: shape (N,)
    """
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    matrix_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    return matrix_norms @ query_norm


def top_k_chunks(
    question_embedding: np.ndarray,
    chunk_embeddings: np.ndarray,
    chunks: list[str],
    k: int = 4,
) -> list[str]:
    """
    Return the top-k chunks most similar to the question embedding.

    Args:
        question_embedding: shape (D,)
        chunk_embeddings:   shape (N, D)
        chunks:             list of N text strings
        k:                  number of chunks to return

    Returns:
        Ordered list of up to k most relevant chunk strings.
    """
    if len(chunks) == 0:
        return []
    k = min(k, len(chunks))
    sims = cosine_similarity(question_embedding, chunk_embeddings)
    top_indices = np.argsort(sims)[::-1][:k]
    return [chunks[i] for i in top_indices]
