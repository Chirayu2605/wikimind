"""
generation.py — LLM prompt construction and API calls via OpenAI.

Two prompts:
1. generate_answer()         — grounds the answer in retrieved Wikipedia chunks.
2. generate_similar_questions() — suggests follow-up questions based on the topic summary.
"""

from __future__ import annotations

from openai import OpenAI

from app import config


def _get_client() -> OpenAI:
    kwargs = {"api_key": config.OPENAI_API_KEY or "dummy-key"}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    return OpenAI(**kwargs)


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

ANSWER_SYSTEM_PROMPT = """\
You are a knowledgeable assistant that answers questions using ONLY the provided Wikipedia context.
Rules:
- Base your answer exclusively on the context passages provided.
- If the context does not contain enough information to answer the question, say so clearly — do NOT invent information.
- Be concise but thorough. Use complete sentences.
- Do not reference the context passages by name (e.g., do not say "According to passage 1…").
"""

ANSWER_USER_TEMPLATE = """\
Context passages from Wikipedia:
---
{context}
---

Question: {question}

Answer:"""


def generate_answer(question: str, context_chunks: list[str]) -> str:
    """
    Ask the LLM to answer `question` using only the provided `context_chunks`.
    Returns the answer as a string.
    """
    context = "\n\n".join(context_chunks)
    user_message = ANSWER_USER_TEMPLATE.format(context=context, question=question)

    response = _get_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Similar questions generation
# ---------------------------------------------------------------------------

SIMILAR_Q_SYSTEM_PROMPT = """\
You generate interesting follow-up questions that someone might want to ask after reading about a topic.
Produce exactly 5 questions, one per line, with no numbering or bullet points.
Make them specific, intellectually interesting, and directly related to the topic.
"""

SIMILAR_Q_USER_TEMPLATE = """\
Topic summary:
{summary}

Generate 5 follow-up questions:"""


def generate_similar_questions(topic_summary: str) -> list[str]:
    """
    Generate a list of 5 follow-up questions based on the topic summary.
    Returns a list of question strings.
    """
    user_message = SIMILAR_Q_USER_TEMPLATE.format(summary=topic_summary[:2000])

    response = _get_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": SIMILAR_Q_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()
    questions = [q.strip() for q in raw.splitlines() if q.strip()]
    return questions[:5]
