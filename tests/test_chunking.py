"""
test_chunking.py — Unit tests for the text chunking module.
"""

import pytest
from app.chunking import chunk_text, TARGET_WORDS, OVERLAP_WORDS


SAMPLE_TEXT = "\n\n".join(
    [f"Paragraph {i}. " + ("This is a sample sentence with some filler words to hit the word target. " * 6)
     for i in range(1, 20)]
)


def test_returns_list_of_strings():
    chunks = chunk_text(SAMPLE_TEXT)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)


def test_nonempty_input_produces_chunks():
    chunks = chunk_text(SAMPLE_TEXT)
    assert len(chunks) > 0


def test_empty_input_returns_empty_list():
    assert chunk_text("") == []


def test_chunk_sizes_near_target():
    chunks = chunk_text(SAMPLE_TEXT)
    word_counts = [len(c.split()) for c in chunks]
    # All chunks except possibly the last should be at least half the target
    for wc in word_counts[:-1]:
        assert wc >= TARGET_WORDS * 0.5, f"Chunk too small: {wc} words"
    # No chunk should be more than ~3x the target
    for wc in word_counts:
        assert wc <= TARGET_WORDS * 3, f"Chunk too large: {wc} words"


def test_overlap_content_is_present():
    """The last OVERLAP_WORDS words of chunk[0] should appear in chunk[1]."""
    chunks = chunk_text(SAMPLE_TEXT)
    if len(chunks) < 2:
        pytest.skip("Not enough chunks to test overlap")
    prev_words = chunks[0].split()
    tail = " ".join(prev_words[-OVERLAP_WORDS:])
    assert tail in chunks[1], "Overlap from previous chunk not found in next chunk"


def test_single_paragraph_returns_one_chunk():
    single = "Word " * 100
    chunks = chunk_text(single)
    assert len(chunks) == 1


def test_whitespace_only_input_returns_empty():
    assert chunk_text("   \n\n   \n   ") == []
