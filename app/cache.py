"""
cache.py — Redis helpers for storing and retrieving Wikipedia pages + embeddings.

Serialization strategy:
- Page text/metadata → JSON (human-readable, easy to inspect with redis-cli)
- NumPy chunk embeddings → raw bytes via ndarray.tobytes() with shape stored separately.
  We do NOT use pickle for embeddings: tobytes() is simpler and has no deserialization risk.

Key scheme:
  wiki:page:<title>      → JSON with title, summary, full_text, links, categories, chunks
  wiki:emb:<title>       → raw bytes of float32 ndarray
  wiki:emb_shape:<title> → JSON list [rows, cols]
"""

from __future__ import annotations

import json
import numpy as np
import redis

from app.config import REDIS_URL, REDIS_TTL_SECONDS
from app.wiki_fetch import PageData


def _client() -> redis.Redis:
    """Return a Redis client.  Connections are pooled by the redis-py library."""
    return redis.from_url(REDIS_URL, decode_responses=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cached_page(title: str) -> tuple[PageData, list[str], np.ndarray] | None:
    """
    Return (PageData, chunks, embeddings) from Redis, or None on cache miss.
    Returns None gracefully if Redis is unavailable.
    """
    try:
        r = _client()
        key_page = f"wiki:page:{title}"
        key_emb = f"wiki:emb:{title}"
        key_shape = f"wiki:emb_shape:{title}"

        raw_page = r.get(key_page)
        if raw_page is None:
            return None

        page_dict = json.loads(raw_page)
        page_data = PageData(
            title=page_dict["title"],
            summary=page_dict["summary"],
            full_text=page_dict["full_text"],
            links=page_dict["links"],
            categories=page_dict["categories"],
        )
        chunks: list[str] = page_dict["chunks"]

        raw_emb = r.get(key_emb)
        raw_shape = r.get(key_shape)
        if raw_emb is None or raw_shape is None:
            return None

        shape = tuple(json.loads(raw_shape))
        embeddings = np.frombuffer(raw_emb, dtype=np.float32).reshape(shape)
        return page_data, chunks, embeddings
    except Exception:
        return None  # Treat any Redis error as a cache miss


def set_cached_page(
    title: str,
    page_data: PageData,
    chunks: list[str],
    embeddings: np.ndarray,
) -> None:
    """
    Persist page data, chunks, and embeddings to Redis with REDIS_TTL_SECONDS TTL.
    Silently skips caching if Redis is unavailable.
    """
    try:
        r = _client()
        key_page = f"wiki:page:{title}"
        key_emb = f"wiki:emb:{title}"
        key_shape = f"wiki:emb_shape:{title}"

        page_dict = {
            "title": page_data.title,
            "summary": page_data.summary,
            "full_text": page_data.full_text,
            "links": page_data.links,
            "categories": page_data.categories,
            "chunks": chunks,
        }
        r.setex(key_page, REDIS_TTL_SECONDS, json.dumps(page_dict))
        r.setex(key_emb, REDIS_TTL_SECONDS, embeddings.astype(np.float32).tobytes())
        r.setex(key_shape, REDIS_TTL_SECONDS, json.dumps(list(embeddings.shape)))
    except Exception:
        pass  # Caching is best-effort; don't crash the request if Redis is down


def is_redis_available() -> bool:
    """Ping Redis; return True if reachable."""
    try:
        return _client().ping()
    except Exception:
        return False
