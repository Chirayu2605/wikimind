"""
test_retrieval.py — Unit tests for the cosine-similarity retrieval module.
"""

import numpy as np
import pytest
from app.retrieval import cosine_similarity, top_k_chunks


def test_cosine_similarity_identical_vectors():
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    matrix = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    sims = cosine_similarity(v, matrix)
    assert np.isclose(sims[0], 1.0)


def test_cosine_similarity_orthogonal_vectors():
    v = np.array([1.0, 0.0], dtype=np.float32)
    matrix = np.array([[0.0, 1.0]], dtype=np.float32)
    sims = cosine_similarity(v, matrix)
    assert np.isclose(sims[0], 0.0, atol=1e-6)


def test_cosine_similarity_returns_correct_shape():
    query = np.random.rand(64).astype(np.float32)
    matrix = np.random.rand(10, 64).astype(np.float32)
    sims = cosine_similarity(query, matrix)
    assert sims.shape == (10,)


def test_top_k_returns_correct_count():
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    embeddings = np.random.rand(8, 3).astype(np.float32)
    chunks = [f"chunk {i}" for i in range(8)]
    result = top_k_chunks(query, embeddings, chunks, k=3)
    assert len(result) == 3


def test_top_k_returns_best_chunk():
    """The chunk whose embedding is closest to the query should rank first."""
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    # Make chunk at index 2 perfectly aligned with the query
    embeddings = np.random.rand(5, 3).astype(np.float32) * 0.1
    embeddings[2] = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    chunks = [f"chunk {i}" for i in range(5)]
    result = top_k_chunks(query, embeddings, chunks, k=1)
    assert result[0] == "chunk 2"


def test_top_k_empty_chunks_returns_empty():
    query = np.array([1.0, 0.0], dtype=np.float32)
    embeddings = np.empty((0, 2), dtype=np.float32)
    result = top_k_chunks(query, embeddings, [], k=3)
    assert result == []


def test_top_k_clamps_to_available_chunks():
    query = np.array([1.0, 0.0], dtype=np.float32)
    embeddings = np.random.rand(2, 2).astype(np.float32)
    chunks = ["a", "b"]
    result = top_k_chunks(query, embeddings, chunks, k=10)
    assert len(result) == 2
