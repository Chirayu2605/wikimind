"""
config.py — Load environment variables for the app.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL", None)
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_TTL_SECONDS: int = int(os.getenv("REDIS_TTL_SECONDS", str(7 * 24 * 3600)))  # 7 days

# Retrieval
TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "4"))
