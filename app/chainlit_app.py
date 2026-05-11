"""Chainlit UI for HR Document Search.

Pipeline: retriever (hybrid + RRF) -> reranker (cross-encoder) -> Ollama.

Users can **attach PDF / DOCX / TXT / MD** with a message to index into Qdrant
immediately (same pipeline as `scripts/ingest_folder.py`), then ask questions
in the same or next messages. Chat-only flow still works when no file is attached.

Each answer carries Chainlit Source elements so users can click citations to
inspect the exact chunk that grounded the answer.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import chainlit as cl

from src.config import get_settings
from src.generation.llm import OllamaLLM
from src.generation.prompts import build_prompt
from src.ingestion.indexer import Indexer
from src.search.embedder import BGEEmbedder
from src.search.reranker import CrossEncoderReranker
from src.search.retriever import HybridRetriever
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Lazy-loaded singletons so UI starts fast and models are only warmed on first use.
_embedder: BGEEmbedder | None = None
_indexer: Indexer | None = None
_retriever: HybridRetriever | None = None
_reranker: CrossEncoderReranker | None = None
_llm: OllamaLLM | None = None

UPLOAD_EXTS = {".pdf", ".docx", ".txt", ".md"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_SKIP_ELEMENT_TYPES = frozenset({"image", "audio", "video"})


def _ensure_embedder() -> BGEEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = BGEEmbedder()
    return _embedder


def _get_indexer() -> Indexer:
    global _indexer
    if _indexer is None:
        _indexer = Indexer(embedder=_ensure_embedder())
    return _indexer


def _get_components() -> tuple[HybridRetriever, CrossEncoderReranker, OllamaLLM]:
    global _retriever, _reranker, _llm
    emb = _ensure_embedder()
    if _retriever is None:
        _retriever = HybridRetriever(embedder=emb)
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    if _llm is None:
        _llm = OllamaLLM()
    return _retriever, _reranker, _llm


def _format_source_display(meta: dict[str, Any], rerank_score: float) -> str:
    filename = meta.get("source", "unknown")
    page = meta.get("page", "?")
    return f"{filename} — Trang {page}  (score {rerank_score:.3f})"


async def _run_blocking(fn, *args, **kwargs):
    """Run a blocking function in a worker thread so Chainlit stays responsive."""
    return await asyncio.to_thread(fn, *args, **kwargs)


def _ingest_one_uploaded_file(src_path: Path, display_name: str) -> str:
    """Copy to a path with correct suffix, ingest, delete temp. Returns user-facing line."""
    ext = Path(display_name).suffix.lower()
    if not ext:
        ext = src_path.suffix.lower()
    if ext not in UPLOAD_EXTS:
        return f"**Bỏ qua** `{display_name}` — chỉ hỗ trợ {', '.join(sorted(UPLOAD_EXTS))}."
    if not src_path.is_file():
        return f"**Lỗi** `{display_name}` — không đọc được file tạm."
    size = src_path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        return f"**Bỏ qua** `{display_name}` — vượt quá 50MB."

    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
            tmp = Path(tf.name)
        shutil.copy2(src_path, tmp)
        indexer = _get_indexer()
        summary = indexer.ingest_file(
            tmp,
            extra_meta={
                "source": display_name,
                "doc_type": "upload",
                "department": "chainlit",
            },
        )
        n = summary["chunks_indexed"]
        if n == 0:
            return f"**Không có nội dung** sau khi parse `{display_name}` (file rỗng hoặc không trích được chữ)."
        return (
            f"**Đã index** `{display_name}` → **{n}** chunk "
            f"(document_id: `{summary['document_id']}`)."
        )
    except Exception as e:
        logger.exception("Ingest upload failed for %s", display_name)
        return f"**Lỗi index** `{display_name}`: {e}"
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


async def _handle_uploads(message: cl.Message) -> list[str]:
    """Process Chainlit spontaneous file uploads attached to the user message."""
    lines: list[str] = []
    for el in message.elements or []:
        el_type = getattr(el, "type", None) or ""
        if el_type in _SKIP_ELEMENT_TYPES:
            continue
        raw_path = getattr(el, "path", None)
        if not raw_path:
            continue
        src = Path(str(raw_path))
        name = getattr(el, "name", None) or src.name or "upload"
        lines.append(await _run_blocking(_ingest_one_uploaded_file, src, name))
    return lines


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="Ngày phép",
            message="Nhân viên được nghỉ phép tối đa bao nhiêu ngày mỗi năm?",
        ),
        cl.Starter(
            label="Quy trình nghỉ việc",
            message="Quy trình xin nghỉ việc gồm những bước nào?",
        ),
        cl.Starter(
            label="Lương thử việc",
            message="Mức lương thử việc so với lương chính thức chênh lệch bao nhiêu?",
        ),
        cl.Starter(
            label="Chính sách WFH",
            message="Chính sách làm việc từ xa của công ty như thế nào?",
        ),
    ]


@cl.on_chat_start
async def on_chat_start() -> None:
    # Welcome screen is rendered from `chainlit.md`.
    # Keep this hook empty to avoid a duplicate greeting.
    return None


@cl.on_message
async def on_message(message: cl.Message) -> None:
    question = (message.content or "").strip()

    if message.elements:
        ingest_lines = await _handle_uploads(message)
        if ingest_lines:
            await cl.Message(
                content="### Kết quả upload / index\n\n" + "\n\n".join(ingest_lines),
                author="HR Assistant",
            ).send()

    if not question:
        if not message.elements:
            await cl.Message(
                content="Vui lòng nhập câu hỏi, hoặc đính kèm file PDF/DOCX/TXT/MD để index.",
                author="HR Assistant",
            ).send()
        return

    retriever, reranker, llm = _get_components()
    settings = get_settings()

    answer_msg = cl.Message(content="", author="HR Assistant")
    await answer_msg.send()

    stage_timings: dict[str, int] = {}

    # --- Retrieval ---
    async with cl.Step(name="🔍 Hybrid search (dense + sparse)", type="retrieval") as step:
        t0 = time.perf_counter()
        retrieved = await _run_blocking(
            retriever.search, question, limit=settings.top_k_retrieve
        )
        stage_timings["search_ms"] = int((time.perf_counter() - t0) * 1000)
        step.output = f"Lấy {len(retrieved)} chunks ứng viên trong {stage_timings['search_ms']} ms"

    if not retrieved:
        answer_msg.content = (
            "Tài liệu hiện tại không có thông tin về vấn đề này. "
            "Vui lòng thử đính kèm thêm tài liệu liên quan hoặc đổi cách đặt câu hỏi."
        )
        await answer_msg.update()
        return

    # --- Rerank ---
    async with cl.Step(name="🎯 Cross-encoder rerank", type="rerank") as step:
        t0 = time.perf_counter()
        reranked = await _run_blocking(
            reranker.rerank, question, retrieved, settings.top_k_rerank
        )
        stage_timings["rerank_ms"] = int((time.perf_counter() - t0) * 1000)
        step.output = (
            f"Chọn top-{len(reranked)} trong {stage_timings['rerank_ms']} ms · "
            f"best score = {reranked[0]['rerank_score']:.3f}"
        )

    # --- Generate ---
    async with cl.Step(name="🧠 Qwen3-8B generate", type="llm") as step:
        prompt = build_prompt(question, reranked)
        step.input = prompt[:1500] + ("..." if len(prompt) > 1500 else "")
        t0 = time.perf_counter()
        answer = await _run_blocking(llm.generate, question, reranked)
        stage_timings["generate_ms"] = int((time.perf_counter() - t0) * 1000)
        step.output = f"{len(answer)} ký tự trong {stage_timings['generate_ms']} ms"

    # --- Build source elements (native citation viewer) ---
    source_elements: list[cl.Text] = []
    source_names: list[str] = []
    for i, chunk in enumerate(reranked, start=1):
        meta = chunk.get("metadata", {}) or {}
        display = _format_source_display(meta, float(chunk.get("rerank_score", 0.0)))
        name = f"[{i}] {display}"
        source_names.append(name)
        source_elements.append(
            cl.Text(name=name, content=chunk.get("text", ""), display="side")
        )

    total_ms = sum(stage_timings.values())
    footer = (
        "\n\n---\n"
        f"_⏱ {total_ms} ms  ·  search {stage_timings['search_ms']} ms  ·  "
        f"rerank {stage_timings['rerank_ms']} ms  ·  generate {stage_timings['generate_ms']} ms_"
    )
    if source_names:
        footer = "\n\n**Nguồn:** " + ", ".join(source_names) + footer

    answer_msg.content = answer + footer
    answer_msg.elements = source_elements
    await answer_msg.update()
