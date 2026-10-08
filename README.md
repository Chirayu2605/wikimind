# WikiMind — Wikipedia Q&A Assistant

> Ask any question → get a grounded, AI-generated answer sourced directly from Wikipedia.

**Tech stack:** FastAPI · sentence-transformers · OpenAI / Groq · Redis · Vanilla JS

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)](https://redis.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What it does

WikiMind accepts a natural-language question, automatically finds the most relevant Wikipedia page, breaks it into semantically-meaningful chunks, embeds them with a local sentence-transformer model, retrieves the top-4 most relevant passages via cosine similarity, and uses an LLM to produce a grounded answer — together with follow-up questions and related topics.

Everything is cached in Redis so repeated questions are served in milliseconds.

---

## Architecture

```
Browser
  │
  ▼  POST /ask { "question": "..." }
  │
  ├─ 1. MediaWiki API → search → best page title
  │
  ├─ 2. Redis cache check
  │      HIT  → page text + chunk embeddings loaded from cache
  │      MISS → fetch full page → chunk (~300 words, 50-word overlap)
  │                             → embed (all-MiniLM-L6-v2, local)
  │                             → store in Redis (7-day TTL)
  │
  ├─ 3. Embed the question (same local model)
  │
  ├─ 4. Cosine similarity (NumPy) → top-4 chunks
  │
  ├─ 5. LLM call → grounded answer (context-only, no hallucination)
  │
  ├─ 6. LLM call → 5 follow-up questions
  │
  └─ 7. Assemble JSON response → rendered in browser
```

---

## Project Structure

```
wiki-qa-assistant/
├── app/
│   ├── main.py          # FastAPI app + 7-step pipeline
│   ├── models.py        # Pydantic request / response schemas
│   ├── wiki_fetch.py    # MediaWiki Action API (no wrapper lib)
│   ├── chunking.py      # Paragraph-based chunker with overlap
│   ├── embeddings.py    # sentence-transformers singleton
│   ├── retrieval.py     # NumPy cosine similarity retrieval
│   ├── generation.py    # LLM prompts + OpenAI-compatible calls
│   ├── cache.py         # Redis helpers (fault-tolerant)
│   └── config.py        # env var loading via python-dotenv
├── frontend/
│   ├── index.html
│   ├── style.css        # Dark glassmorphism design
│   └── app.js
├── tests/
│   ├── test_api.py      # FastAPI integration tests (all mocked)
│   ├── test_chunking.py
│   └── test_retrieval.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Quick Start — Docker (recommended)

```bash
# 1. Clone
git clone https://github.com/Chirayu2605/wikimind.git
cd wikimind

# 2. Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY (or Groq key)

# 3. Build and run (app + Redis)
docker compose up --build

# 4. Open
open http://localhost:8000          # frontend
open http://localhost:8000/docs     # interactive API docs
```

---

## Quick Start — Local (no Docker)

```bash
# Requires Python 3.11+ and Redis running locally

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Start Redis (one-liner with Docker)
docker run -d -p 6379:6379 redis:7-alpine

cp .env.example .env
# Edit .env — set OPENAI_API_KEY and REDIS_URL=redis://localhost:6379

uvicorn app.main:app --reload
# → http://localhost:8000
```

---

## LLM Providers

WikiMind works with any **OpenAI-compatible** API:

| Provider | `OPENAI_BASE_URL` | Free tier |
|---|---|---|
| OpenAI | *(leave blank)* | No |
| [Groq](https://console.groq.com) | `https://api.groq.com/openai/v1` | ✅ Yes |
| Ollama (local) | `http://localhost:11434/v1` | ✅ Yes |

---

## Running Tests

```bash
pytest tests/ -v
# 20 tests, all pass. External calls (Wikipedia, Redis, LLM) are mocked.
```

---

## Example Queries

| Question | Wikipedia page resolved |
|---|---|
| How does photosynthesis work? | Photosynthesis |
| What caused World War I? | World War I |
| Explain neural networks | Artificial neural network |
| What is quantum entanglement? | Quantum entanglement |
| Who was Nikola Tesla? | Nikola Tesla |

---

## API Reference

### `POST /ask`

```json
// Request
{ "question": "How does photosynthesis work?" }

// Response
{
  "answer": "Photosynthesis is the process by which...",
  "extra_info": "Photosynthesis is a system of biological...",
  "related_topics": ["Chlorophyll", "Calvin cycle", "..."],
  "similar_questions": ["What role does chlorophyll play?", "..."],
  "sources": ["Chunk text 1...", "Chunk text 2...", "..."],
  "page_title": "Photosynthesis",
  "cached": false
}
```

### `GET /health`

```json
{ "status": "ok", "redis": true }
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **No LangChain** | Every step is explicit — chunking, embedding, retrieval, caching are all written from scratch so the mechanics are fully auditable |
| **Local sentence-transformers** | Zero API cost for embeddings; `all-MiniLM-L6-v2` loads once as a module singleton |
| **NumPy cosine similarity** | Adequate for single-page retrieval (≤ 100 chunks); no vector DB overhead |
| **`tobytes()` not pickle** | Storing NumPy arrays in Redis as raw bytes avoids pickle deserialization risks |
| **MediaWiki API directly** | No third-party `wikipedia` wrapper; HTTP behaviour is transparent and controllable |
| **Fault-tolerant cache** | Redis downtime degrades to cache-miss, never a 500 error |

---

## License

MIT
