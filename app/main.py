"""
main.py — FastAPI application entry point.

Pipeline on POST /ask:
  1. Search Wikipedia for the best-matching page title
  2. Check Redis cache → HIT: load page+chunks+embeddings  |  MISS: fetch+chunk+embed+cache
  3. Embed the question
  4. Cosine-similarity retrieval → top-k chunks
  5. LLM → grounded answer
  6. LLM → similar questions
  7. Assemble and return AskResponse
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import AskRequest, AskResponse
from app.wiki_fetch import search_page, get_page_content
from app.chunking import chunk_text
from app.embeddings import embed
from app.retrieval import top_k_chunks
from app.generation import generate_answer, generate_similar_questions
from app import cache
from app.config import TOP_K_CHUNKS

import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wikipedia Q&A Assistant",
    description=(
        "Ask any question and get a grounded answer sourced from Wikipedia. "
        "Powered by semantic search (sentence-transformers), OpenAI for generation, "
        "and Redis for caching fetched pages and embeddings."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files will be mounted at the bottom of the file after API routes




@app.get("/health")
def health():
    """Basic liveness check."""
    return {
        "status": "ok",
        "redis": cache.is_redis_available(),
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """
    Main Q&A endpoint.

    Accepts a free-form question, resolves the most relevant Wikipedia page,
    retrieves the most relevant passages semantically, and returns a grounded
    answer together with extra info, related topics, and suggested follow-ups.
    """
    question = request.question.strip()
    logger.info("Received question: %r", question)
    t0 = time.perf_counter()

    # ── Step 1: Resolve Wikipedia page title ──────────────────────────────
    try:
        title = search_page(question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    logger.info("Resolved page title: %r", title)

    # ── Step 2: Cache check ───────────────────────────────────────────────
    cached_result = cache.get_cached_page(title)
    was_cached = cached_result is not None

    if was_cached:
        page_data, chunks, chunk_embeddings = cached_result
        logger.info("Cache HIT for %r (%.2fs so far)", title, time.perf_counter() - t0)
    else:
        logger.info("Cache MISS for %r — fetching from Wikipedia", title)
        try:
            page_data = get_page_content(title)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        chunks = chunk_text(page_data.full_text)
        if not chunks:
            raise HTTPException(status_code=422, detail=f"Could not extract content from Wikipedia page: {title!r}")

        chunk_embeddings = embed(chunks)
        cache.set_cached_page(title, page_data, chunks, chunk_embeddings)
        logger.info("Fetched, chunked, embedded, cached %r (%.2fs so far)", title, time.perf_counter() - t0)

    # ── Step 3: Embed the question ────────────────────────────────────────
    question_embedding = embed([question])[0]

    # ── Step 4: Retrieve top-k chunks ─────────────────────────────────────
    top_chunks = top_k_chunks(question_embedding, chunk_embeddings, chunks, k=TOP_K_CHUNKS)

    # ── Step 5: Generate answer ───────────────────────────────────────────
    answer = generate_answer(question, top_chunks)

    # ── Step 6: Generate similar questions ───────────────────────────────
    similar_questions = generate_similar_questions(page_data.summary)

    # ── Step 7: Assemble related topics (links + categories) ──────────────
    related_topics = (page_data.categories + page_data.links)[:15]

    elapsed = time.perf_counter() - t0
    logger.info("Request completed in %.2fs (cached=%s)", elapsed, was_cached)

    return AskResponse(
        answer=answer,
        extra_info=page_data.summary,
        related_topics=related_topics,
        similar_questions=similar_questions,
        sources=[chunk[:300] + "…" if len(chunk) > 300 else chunk for chunk in top_chunks],
        page_title=title,
        cached=was_cached,
    )


# Serve frontend static files
_static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(_static_dir, "index.html"))


