"""Recursive text chunking with configurable size and overlap."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _make_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
    )


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 128,
    metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """Split a single text into chunks with overlap."""
    if not text or not text.strip():
        return []
    splitter = _make_splitter(chunk_size, overlap)
    parts = splitter.split_text(text)
    base_meta = dict(metadata or {})
    chunks: list[Chunk] = []
    for i, part in enumerate(parts):
        meta = dict(base_meta)
        meta["chunk_index"] = i
        meta["char_count"] = len(part)
        chunks.append(Chunk(text=part, metadata=meta))
    return chunks


def chunk_documents(
    docs: list,  # list[ParsedDocument]
    chunk_size: int = 512,
    overlap: int = 128,
) -> list[Chunk]:
    """Chunk a list of ParsedDocument, preserving per-page metadata."""
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(
            chunk_text(
                text=doc.text,
                chunk_size=chunk_size,
                overlap=overlap,
                metadata=doc.metadata,
            )
        )
    return all_chunks
