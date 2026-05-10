"""Pydantic request / response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks_indexed: int
    processing_time_ms: int


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = 5
    department_filter: str | None = None
    doc_type_filter: str | None = None


class SourceItem(BaseModel):
    document_id: str | None = None
    filename: str
    page: int | None = None
    score: float
    excerpt: str


class StageMs(BaseModel):
    embed: int = 0
    search: int = 0
    rerank: int = 0
    generate: int = 0


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    latency_ms: int
    stage_ms: StageMs


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    doc_type: str | None = None
    department: str | None = None
    pages: int
    chunks_count: int


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentSummary]


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    ollama: str
