"""
models.py — Pydantic request / response models.
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="The question or topic to ask about")


class AskResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer generated from Wikipedia context")
    extra_info: str = Field(..., description="Wikipedia summary / introductory information")
    related_topics: list[str] = Field(..., description="Related Wikipedia links / categories")
    similar_questions: list[str] = Field(..., description="LLM-suggested follow-up questions")
    sources: list[str] = Field(..., description="Chunk excerpts used as context for the answer")
    page_title: str = Field(..., description="Wikipedia page title used to answer the question")
    cached: bool = Field(..., description="Whether the page was served from Redis cache")
