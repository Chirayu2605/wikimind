"""
test_api.py — Integration tests for the FastAPI endpoints.

Uses FastAPI's TestClient (wraps httpx) so no real server is needed.
The Wikipedia fetch, embedding, and LLM calls are mocked to keep tests
fast, deterministic, and free of external dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# ── Reusable fixtures / mock data ─────────────────────────────────────────

MOCK_TITLE = "Photosynthesis"
MOCK_SUMMARY = "Photosynthesis is the process by which plants convert sunlight into energy."
MOCK_FULL_TEXT = (MOCK_SUMMARY + " ") * 100  # enough text to chunk
MOCK_CHUNKS = ["Chunk A about photosynthesis.", "Chunk B about chlorophyll.", "Chunk C about glucose."]
MOCK_EMBEDDINGS = np.random.rand(3, 384).astype(np.float32)
MOCK_ANSWER = "Plants use sunlight to convert CO2 and water into glucose via photosynthesis."
MOCK_SIMILAR = [
    "What role does chlorophyll play in photosynthesis?",
    "How do C3 and C4 plants differ?",
    "What happens to oxygen produced during photosynthesis?",
    "How does light intensity affect photosynthesis rate?",
    "What is the Calvin cycle?",
]

from app.wiki_fetch import PageData

MOCK_PAGE_DATA = PageData(
    title=MOCK_TITLE,
    summary=MOCK_SUMMARY,
    full_text=MOCK_FULL_TEXT,
    links=["Chlorophyll", "Glucose", "Light-independent reactions"],
    categories=["Photosynthesis", "Plant biology"],
)


# ── Tests ─────────────────────────────────────────────────────────────────

def test_health_endpoint():
    with patch("app.main.cache.is_redis_available", return_value=True):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "redis" in data


@patch("app.main.cache.get_cached_page", return_value=None)
@patch("app.main.cache.set_cached_page", return_value=None)
@patch("app.main.search_page", return_value=MOCK_TITLE)
@patch("app.main.get_page_content", return_value=MOCK_PAGE_DATA)
@patch("app.main.chunk_text", return_value=MOCK_CHUNKS)
@patch("app.main.embed", return_value=MOCK_EMBEDDINGS)
@patch("app.main.generate_answer", return_value=MOCK_ANSWER)
@patch("app.main.generate_similar_questions", return_value=MOCK_SIMILAR)
def test_ask_returns_correct_shape(
    mock_similar, mock_answer, mock_embed, mock_chunk,
    mock_get_page, mock_search, mock_set_cache, mock_get_cache
):
    resp = client.post("/ask", json={"question": "How does photosynthesis work?"})
    assert resp.status_code == 200
    data = resp.json()

    assert "answer" in data
    assert "extra_info" in data
    assert "related_topics" in data
    assert "similar_questions" in data
    assert "sources" in data
    assert "page_title" in data
    assert "cached" in data

    assert isinstance(data["related_topics"], list)
    assert isinstance(data["similar_questions"], list)
    assert isinstance(data["sources"], list)
    assert data["answer"] == MOCK_ANSWER
    assert data["page_title"] == MOCK_TITLE
    assert data["cached"] is False


@patch("app.main.cache.get_cached_page", return_value=(MOCK_PAGE_DATA, MOCK_CHUNKS, MOCK_EMBEDDINGS))
@patch("app.main.search_page", return_value=MOCK_TITLE)
@patch("app.main.embed", return_value=MOCK_EMBEDDINGS)
@patch("app.main.generate_answer", return_value=MOCK_ANSWER)
@patch("app.main.generate_similar_questions", return_value=MOCK_SIMILAR)
def test_ask_returns_cached_flag_when_cached(
    mock_similar, mock_answer, mock_embed, mock_search, mock_cache
):
    resp = client.post("/ask", json={"question": "Photosynthesis"})
    assert resp.status_code == 200
    assert resp.json()["cached"] is True


@patch("app.main.search_page", side_effect=ValueError("No Wikipedia page found"))
def test_ask_returns_404_when_no_page_found(mock_search):
    resp = client.post("/ask", json={"question": "xyzzy1234nonsense"})
    assert resp.status_code == 404


def test_ask_rejects_empty_question():
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422  # Pydantic validation error


def test_ask_rejects_missing_question():
    resp = client.post("/ask", json={})
    assert resp.status_code == 422
