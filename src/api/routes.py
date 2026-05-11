"""FastAPI routes for upload, chat, search, documents, health."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentSummary,
    HealthResponse,
    SearchResponse,
    SearchResult,
    SourceItem,
    StageMs,
    UploadResponse,
)
from src.config import get_settings
from src.generation.llm import OllamaLLM
from src.ingestion.indexer import Indexer
from src.search.embedder import BGEEmbedder
from src.search.reranker import CrossEncoderReranker
from src.search.retriever import HybridRetriever
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Module-level singletons, created lazily on first access.
_embedder: BGEEmbedder | None = None
_reranker: CrossEncoderReranker | None = None
_retriever: HybridRetriever | None = None
_indexer: Indexer | None = None
_llm: OllamaLLM | None = None


def get_embedder() -> BGEEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = BGEEmbedder()
    return _embedder


def get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(embedder=get_embedder())
    return _retriever


def get_indexer() -> Indexer:
    global _indexer
    if _indexer is None:
        _indexer = Indexer(embedder=get_embedder())
    return _indexer


def get_llm() -> OllamaLLM:
    global _llm
    if _llm is None:
        _llm = OllamaLLM()
    return _llm


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str | None = Form(None),
    department: str | None = Form(None),
    indexer: Indexer = Depends(get_indexer),
) -> UploadResponse:
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_BYTES:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File exceeds 50MB limit")
            tmp.write(chunk)
        tmp_path = Path(tmp.name)

    try:
        extra_meta: dict[str, Any] = {}
        if doc_type:
            extra_meta["doc_type"] = doc_type
        if department:
            extra_meta["department"] = department
        # Preserve the original filename as the source in metadata.
        extra_meta["source"] = filename

        start = time.perf_counter()
        summary = indexer.ingest_file(tmp_path, extra_meta=extra_meta)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return UploadResponse(
            document_id=summary["document_id"],
            filename=filename,
            pages=summary["pages"],
            chunks_indexed=summary["chunks_indexed"],
            processing_time_ms=elapsed_ms,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def _build_filter(department: str | None, doc_type: str | None) -> dict[str, Any] | None:
    flt: dict[str, Any] = {}
    if department:
        flt["metadata.department"] = department
    if doc_type:
        flt["metadata.doc_type"] = doc_type
    return flt or None


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    reranker: CrossEncoderReranker = Depends(get_reranker),
    llm: OllamaLLM = Depends(get_llm),
) -> ChatResponse:
    settings = get_settings()
    start_total = time.perf_counter()
    filter_dict = _build_filter(req.department_filter, req.doc_type_filter)

    t0 = time.perf_counter()
    retrieved = retriever.search(
        req.question,
        limit=settings.top_k_retrieve,
        filter=filter_dict,
    )
    search_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    top_k = min(req.top_k, settings.top_k_rerank)
    reranked = reranker.rerank(req.question, retrieved, top_k=top_k) if retrieved else []
    rerank_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    if reranked:
        answer = llm.generate(req.question, reranked)
    else:
        answer = (
            "Tài liệu hiện tại không có thông tin về vấn đề này. "
            "Vui lòng liên hệ bộ phận HR để được hỗ trợ."
        )
    generate_ms = int((time.perf_counter() - t0) * 1000)

    sources: list[SourceItem] = []
    for r in reranked:
        meta = r.get("metadata", {}) or {}
        text = r.get("text", "")
        sources.append(
            SourceItem(
                document_id=meta.get("document_id"),
                filename=meta.get("source", ""),
                page=meta.get("page"),
                score=float(r.get("rerank_score", r.get("score", 0.0))),
                excerpt=text[:300],
            )
        )

    total_ms = int((time.perf_counter() - start_total) * 1000)
    return ChatResponse(
        answer=answer,
        sources=sources,
        latency_ms=total_ms,
        stage_ms=StageMs(embed=0, search=search_ms, rerank=rerank_ms, generate=generate_ms),
    )


@router.get("/search", response_model=SearchResponse)
def search(
    q: str,
    k: int = 10,
    department: str | None = None,
    doc_type: str | None = None,
    retriever: HybridRetriever = Depends(get_retriever),
) -> SearchResponse:
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query is empty")
    flt = _build_filter(department, doc_type)
    results = retriever.search(q, limit=k, filter=flt)
    items = [
        SearchResult(
            chunk_id=r["id"],
            text=r["text"],
            metadata=r.get("metadata", {}),
            score=r["score"],
        )
        for r in results
    ]
    return SearchResponse(query=q, results=items, total=len(items))


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(indexer: Indexer = Depends(get_indexer)) -> DocumentListResponse:
    docs = indexer.list_documents()
    items = [
        DocumentSummary(
            document_id=d["document_id"],
            filename=d["filename"],
            doc_type=d.get("doc_type"),
            department=d.get("department"),
            pages=d["pages"],
            chunks_count=d["chunks_count"],
        )
        for d in docs
    ]
    return DocumentListResponse(total=len(items), documents=items)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    indexer: Indexer = Depends(get_indexer),
) -> dict[str, Any]:
    indexer.delete_document(document_id)
    return {"deleted": document_id}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    qdrant_status = "unknown"
    ollama_status = "unknown"

    if settings.qdrant_mode == "local":
        try:
            client = settings.create_qdrant_client()
            client.get_collections()
            qdrant_status = "ok (local)"
        except Exception as e:
            qdrant_status = f"error:{type(e).__name__}"
    else:
        try:
            r = requests.get(f"{settings.qdrant_url}/healthz", timeout=2)
            qdrant_status = "ok" if r.status_code == 200 else f"error:{r.status_code}"
        except Exception as e:
            qdrant_status = f"down:{type(e).__name__}"

    try:
        r = requests.get(f"{settings.ollama_url}/api/tags", timeout=2)
        ollama_status = "ok" if r.status_code == 200 else f"error:{r.status_code}"
    except Exception as e:
        ollama_status = f"down:{type(e).__name__}"

    overall = "ok" if "ok" in qdrant_status and ollama_status == "ok" else "degraded"
    return HealthResponse(status=overall, qdrant=qdrant_status, ollama=ollama_status)
