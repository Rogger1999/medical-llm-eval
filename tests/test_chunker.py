"""Tests for the text chunker service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.chunker import TextChunker, _approx_tokens


def make_chunker():
    session = MagicMock()
    return TextChunker(session)


def test_approx_tokens_basic():
    assert _approx_tokens("hello world") == 2  # 11 chars // 4


def test_chunk_text_produces_chunks():
    chunker = make_chunker()
    text = "Malnutrition affects millions of children worldwide. " * 50
    chunks = chunker._chunk_text(text, doc_id="test-id")
    assert len(chunks) >= 1


def test_chunk_text_correct_fields():
    chunker = make_chunker()
    text = "Children with severe acute malnutrition benefit from RUTF. " * 20
    chunks = chunker._chunk_text(text, doc_id="doc-001")
    for c in chunks:
        assert "doc_id" in c
        assert "chunk_index" in c
        assert "char_start" in c
        assert "char_end" in c
        assert "text" in c
        assert c["doc_id"] == "doc-001"


def test_chunk_index_sequential():
    chunker = make_chunker()
    text = "Word " * 400
    chunks = chunker._chunk_text(text, doc_id="seq-test")
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_overlap_creates_overlap():
    chunker = make_chunker()
    # Create text long enough to need multiple chunks
    long_text = "The intervention showed significant improvement in weight-for-height z-scores. " * 80
    chunks = chunker._chunk_text(long_text, doc_id="overlap-test")
    if len(chunks) >= 2:
        # Check that consecutive chunks share some content (overlap)
        end_of_first = chunks[0]["text"][-50:]
        start_of_second = chunks[1]["text"][:100]
        # At least some overlap: char_end of first > char_start of second
        assert chunks[0]["char_end"] > chunks[1]["char_start"] or len(chunks) == 1


def test_small_text_produces_single_chunk():
    chunker = make_chunker()
    text = "Short text about malnutrition interventions."
    chunks = chunker._chunk_text(text, doc_id="small")
    assert len(chunks) <= 1


def test_simple_chunks_fallback():
    chunker = make_chunker()
    text = "a " * 1000
    chunks = chunker._simple_chunks(text, "doc-x", chunk_size=64, overlap=8, min_size=10)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["char_end"] > c["char_start"]
