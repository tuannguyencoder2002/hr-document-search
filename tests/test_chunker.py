"""Unit tests for the chunker."""

from __future__ import annotations

from src.ingestion.chunker import chunk_text


def test_chunk_empty_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_short_text_returns_single():
    chunks = chunk_text("Short sentence.", chunk_size=512, overlap=128)
    assert len(chunks) == 1
    assert chunks[0].text == "Short sentence."


def test_chunk_size_respected():
    text = "Câu một. " * 500  # ~ 4500 chars
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 200


def test_chunk_metadata_propagates():
    chunks = chunk_text(
        "Some text.",
        chunk_size=512,
        overlap=128,
        metadata={"source": "f.pdf", "page": 3},
    )
    assert chunks[0].metadata["source"] == "f.pdf"
    assert chunks[0].metadata["page"] == 3
    assert chunks[0].metadata["chunk_index"] == 0
    assert "char_count" in chunks[0].metadata


def test_chunk_indices_are_sequential():
    text = "A. " * 400
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    indices = [c.metadata["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))
