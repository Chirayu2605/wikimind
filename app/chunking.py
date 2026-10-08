"""
chunking.py — Split Wikipedia plain text into overlapping chunks.

Strategy:
1. Split on double-newlines (paragraph boundaries).
2. Merge short paragraphs until each chunk reaches ~TARGET_WORDS words.
3. Add OVERLAP_WORDS words of overlap from the end of the previous chunk
   to the beginning of the next — this preserves context across boundaries.
"""

from __future__ import annotations

TARGET_WORDS = 300      # Aim for chunks ~300 words
OVERLAP_WORDS = 50      # Carry forward ~50 words from the previous chunk


def _word_count(text: str) -> int:
    return len(text.split())


def chunk_text(text: str, target_words: int = TARGET_WORDS, overlap_words: int = OVERLAP_WORDS) -> list[str]:
    """
    Split `text` into overlapping chunks of roughly `target_words` words.

    Returns a list of non-empty chunk strings.
    """
    # Step 1: split into paragraphs
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Step 2: merge paragraphs into target-sized chunks
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_words = 0

    for para in raw_paragraphs:
        para_words = _word_count(para)
        if buffer_words + para_words > target_words and buffer:
            # Flush the current buffer as a chunk
            chunks.append(" ".join(buffer))
            buffer = []
            buffer_words = 0
        buffer.append(para)
        buffer_words += para_words

    if buffer:
        chunks.append(" ".join(buffer))

    if not chunks:
        return []

    # Step 3: add overlap — prepend the tail of the previous chunk
    result: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1].split()
        tail = " ".join(prev_words[-overlap_words:]) if len(prev_words) > overlap_words else chunks[i - 1]
        result.append(tail + " " + chunks[i])

    return result
