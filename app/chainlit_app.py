"""Chainlit UI for HR Document Search.

Pure chat interface on top of the existing pipeline:
    retriever (hybrid + RRF) -> reranker (cross-encoder) -> Ollama.

Documents are indexed offline via `scripts/ingest_folder.py` — the UI only
reads from the existing Qdrant collection and never accepts uploads.

Each answer carries Chainlit Source elements so users can click citations to
inspect the exact chunk that grounded the answer.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import chainlit as cl

from src.config import get_settings
from src.generation.llm import OllamaLLM
from src.generation.prompts import build_prompt
from src.search.embedder import BGEEmbedder
from src.search.reranker import CrossEncoderReranker
from src.search.retriever import HybridRetriever
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Lazy-loaded singletons so UI starts fast and models are only warmed on first use.
_embedder: BGEEmbedder | None = None
_retriever: HybridRetriever | None = None
_reranker: CrossEncoderReranker | None = None
_llm: OllamaLLM | None = None


def _get_components() -> tuple[HybridRetriever, CrossEncoderReranker, OllamaLLM]:
    global _embedder, _retriever, _reranker, _llm
    if _embedder is None:
        _embedder = BGEEmbedder()
    if _retriever is None:
        _retriever = HybridRetriever(embedder=_embedder)
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
    settings = get_settings()
    welcome = (
        "### 👋 Trợ lý Nhân sự\n\n"
        "Tôi trả lời câu hỏi về **chính sách, quy trình và quy định** dựa trên "
        "tài liệu HR đã được index sẵn. Mỗi câu trả lời đều kèm **nguồn tham khảo** — "
        "bấm vào để xem đoạn tài liệu gốc.\n\n"
        f"_Model: `{settings.ollama_model}` · Embedding: `{settings.embedding_model}`_"
    )
    await cl.Message(content=welcome, author="HR Assistant").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    question = (message.content or "").strip()
    if not question:
        await cl.Message(content="Vui lòng nhập câu hỏi.", author="HR Assistant").send()
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
            "Vui lòng liên hệ bộ phận HR để được hỗ trợ."
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
