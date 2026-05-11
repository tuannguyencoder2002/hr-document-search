"""Chainlit UI for HR Document Search.

Pipeline: retriever (hybrid + RRF) -> reranker (cross-encoder) -> Ollama.

Users can attach PDF / DOCX / TXT / MD to index on the fly. Chat-only flow
still works when no file is attached. Each answer carries Chainlit Source
elements so users can click citations to inspect the exact chunk.

Greetings and small-talk are short-circuited by `src.generation.intent` to
avoid running the full pipeline (saves ~1-3s per trivial message).
"""

from __future__ import annotations

# Keep this import first so HF libs never try to reach the Hub.
import src.hf_offline  # noqa: F401

import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import chainlit as cl

from src.config import get_settings
from src.generation.intent import RESPONSES, Intent, detect_intent
from src.generation.llm import OllamaLLM
from src.generation.prompts import build_prompt
from src.ingestion.indexer import Indexer
from src.search.embedder import BGEEmbedder
from src.search.image_retriever import ImageRetriever
from src.search.reranker import CrossEncoderReranker
from src.search.retriever import HybridRetriever
from src.utils.logger import get_logger, setup_logging
from src.utils.ollama_health import log_model_status

setup_logging()
logger = get_logger(__name__)

# Lazy-loaded singletons.
_embedder: BGEEmbedder | None = None
_indexer: Indexer | None = None
_retriever: HybridRetriever | None = None
_reranker: CrossEncoderReranker | None = None
_llm: OllamaLLM | None = None
_image_retriever: ImageRetriever | None = None

# One-shot warmup guard.
_warmup_started = False
_warmup_done = asyncio.Event()

UPLOAD_EXTS = {".pdf", ".docx", ".txt", ".md"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_SKIP_ELEMENT_TYPES = frozenset({"audio", "video"})


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


def _get_image_retriever() -> ImageRetriever:
    global _image_retriever
    if _image_retriever is None:
        _image_retriever = ImageRetriever()
    return _image_retriever


def _format_source_display(meta: dict[str, Any], rerank_score: float) -> str:
    filename = meta.get("source", "unknown")
    page = meta.get("page", "?")
    return f"{filename} — Trang {page}  (score {rerank_score:.3f})"


def _build_source_element(name: str, chunk: dict[str, Any]) -> Any:
    """Return the best Chainlit element for a source chunk.

    PDFs: native viewer positioned on the right page, so users can verify the
    excerpt in context. Everything else: text element with the chunk content.
    """
    meta = chunk.get("metadata", {}) or {}
    source_path = meta.get("source_path")
    file_type = (meta.get("file_type") or "").lower()
    page = meta.get("page")

    if file_type == "pdf" and source_path:
        p = Path(source_path)
        if p.is_file():
            try:
                pdf_page = int(page) if page is not None else 1
            except (TypeError, ValueError):
                pdf_page = 1
            return cl.Pdf(
                name=name,
                display="side",
                path=str(p),
                page=max(1, pdf_page),
            )
    return cl.Text(
        name=name,
        content=chunk.get("text", ""),
        display="side",
    )


async def _run_blocking(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


def _warm_models_blocking() -> None:
    """Load embedder + reranker + keep LLM resident. Runs in a worker thread."""
    import time as _time

    # Embedder
    try:
        t0 = _time.perf_counter()
        emb = _ensure_embedder()
        emb.encode("khoi dong")
        logger.info("[warmup] embedder ready in %.2fs", _time.perf_counter() - t0)
    except Exception as e:
        logger.warning("[warmup] embedder FAILED: %s", e)

    # Reranker
    try:
        t0 = _time.perf_counter()
        _, reranker, _ = _get_components()
        reranker.rerank("khoi dong", [{"text": "warm up"}], top_k=1)
        logger.info("[warmup] reranker ready in %.2fs", _time.perf_counter() - t0)
    except Exception as e:
        logger.warning("[warmup] reranker FAILED: %s", e)

    # LLM
    try:
        t0 = _time.perf_counter()
        _, _, llm = _get_components()
        logger.info("[warmup] LLM model=%s keep_alive=%s num_gpu=%s",
                    llm.model, llm.keep_alive, llm.num_gpu)
        out = llm.generate("Xin chao", [{"text": "warm up", "metadata": {}}])
        logger.info("[warmup] LLM ready in %.2fs (sample=%r)",
                    _time.perf_counter() - t0, out[:60])
    except Exception as e:
        logger.warning("[warmup] LLM FAILED: %s", e)

    # Report GPU offload status to confirm Ollama actually put the model on GPU
    try:
        log_model_status()
    except Exception as e:
        logger.warning("[warmup] ollama status check failed: %s", e)


async def _warmup_models_once() -> None:
    """Warm heavy models once per process, in the background."""
    global _warmup_started
    if _warmup_started:
        await _warmup_done.wait()
        return
    _warmup_started = True
    logger.info("Warming up models in background…")
    try:
        await _run_blocking(_warm_models_blocking)
    finally:
        _warmup_done.set()
        logger.info("Warmup finished.")


def _ingest_one_uploaded_file(src_path: Path, display_name: str) -> str:
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


async def _handle_uploads(message: cl.Message) -> tuple[list[str], list[Path]]:
    """Process attached elements on a message.

    Documents (PDF / DOCX / TXT / MD) are ingested into Qdrant. Images are
    returned as query images for reverse-image search — they are NOT indexed.

    Returns (ingest_result_lines, query_image_paths).
    """
    lines: list[str] = []
    query_images: list[Path] = []

    for el in message.elements or []:
        el_type = getattr(el, "type", None) or ""
        if el_type in _SKIP_ELEMENT_TYPES:
            continue
        raw_path = getattr(el, "path", None)
        if not raw_path:
            continue
        src = Path(str(raw_path))
        name = getattr(el, "name", None) or src.name or "upload"
        ext = Path(name).suffix.lower() or src.suffix.lower()

        if ext in IMAGE_EXTS or el_type == "image":
            query_images.append(src)
            continue

        lines.append(await _run_blocking(_ingest_one_uploaded_file, src, name))

    return lines, query_images


def _image_search_blocking(
    image_path: Path | None,
    text_query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """Run CLIP image search (and optionally fuse with text) on a worker thread."""
    retriever = _get_image_retriever()
    results: list[dict[str, Any]] = []
    if image_path is not None:
        results = retriever.search_by_image(image_path, limit=top_k)
    elif text_query.strip():
        results = retriever.search_by_text(text_query, limit=top_k)
    return results


def _build_image_result_elements(
    results: list[dict[str, Any]],
) -> tuple[list[Any], list[str]]:
    """Create side-panel Chainlit elements (image + PDF viewer) for each hit."""
    elements: list[Any] = []
    names: list[str] = []
    for i, hit in enumerate(results, start=1):
        meta = hit.get("metadata", {}) or {}
        filename = meta.get("source", "unknown")
        page = meta.get("page", "?")
        score = float(hit.get("score", 0.0))
        name = f"[{i}] {filename} — Trang {page}  (sim {score:.3f})"
        names.append(name)

        # Inline image preview.
        img_path = meta.get("image_path")
        if img_path and Path(img_path).is_file():
            elements.append(cl.Image(name=name, path=img_path, display="side"))

        # Jump-to-PDF viewer for the page that contains this image.
        source_path = meta.get("source_path")
        if source_path and Path(source_path).is_file() and (meta.get("file_type") == "pdf"):
            try:
                pdf_page = int(page) if page else 1
            except (TypeError, ValueError):
                pdf_page = 1
            elements.append(
                cl.Pdf(
                    name=f"{name} · tài liệu gốc",
                    path=str(source_path),
                    page=max(1, pdf_page),
                    display="side",
                )
            )
    return elements, names


async def _run_image_search(query_image: Path, text_query: str) -> None:
    """End-to-end image-query flow: CLIP search → render hits with sources."""
    settings = get_settings()

    # Wait for base warmup (ensures GPU is ready, avoids first-query jank).
    if not _warmup_done.is_set():
        warming = cl.Message(
            content="⏳ Đang nạp model vào GPU (lần đầu)…",
            author="HR Assistant",
        )
        await warming.send()
        await _warmup_models_once()
        warming.content = "✅ Model đã sẵn sàng."
        await warming.update()

    header = "### 🖼 Tìm ảnh tương tự trong tài liệu"
    if text_query:
        header += f"\n_Truy vấn kết hợp: `{text_query}`_"
    answer_msg = cl.Message(content=header, author="HR Assistant")
    await answer_msg.send()

    async with cl.Step(name="🖼 CLIP image search", type="retrieval") as step:
        t0 = time.perf_counter()
        results = await _run_blocking(
            _image_search_blocking,
            query_image,
            text_query,
            settings.image_top_k,
        )
        step.output = (
            f"Tìm thấy {len(results)} ảnh trong {int((time.perf_counter() - t0) * 1000)} ms"
        )

    if not results:
        answer_msg.content = (
            header
            + "\n\nKhông tìm thấy ảnh tương tự trong tài liệu đã index. "
            "Hãy thử ảnh khác, hoặc đảm bảo tài liệu có chứa ảnh và đã được index lại."
        )
        await answer_msg.update()
        return

    elements, names = _build_image_result_elements(results)

    lines: list[str] = []
    for i, hit in enumerate(results, start=1):
        meta = hit.get("metadata", {}) or {}
        filename = meta.get("source", "unknown")
        page = meta.get("page", "?")
        score = float(hit.get("score", 0.0))
        caption = (meta.get("caption") or "").strip().replace("\n", " ")
        if len(caption) > 160:
            caption = caption[:160] + "…"
        lines.append(
            f"**{i}. {filename}** — Trang {page} · similarity **{score:.3f}**"
            + (f"\n\n> {caption}" if caption else "")
        )

    answer_msg.content = (
        header
        + "\n\n"
        + "\n\n".join(lines)
        + "\n\n**Mở để xem:** " + " · ".join(names)
    )
    answer_msg.elements = elements
    await answer_msg.update()


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
    # Kick off model warmup in the background so the first real query is fast.
    # We don't await it — the user can read the welcome screen while it warms.
    asyncio.create_task(_warmup_models_once())


@cl.on_message
async def on_message(message: cl.Message) -> None:
    question = (message.content or "").strip()
    request_id = f"req_{int(time.time() * 1000)}"
    logger.info("[%s] --- new message: %r (elements=%d)",
                request_id, question[:120], len(message.elements or []))

    # --- Separate docs-to-ingest from images-to-search ---
    ingest_lines: list[str] = []
    query_images: list[Path] = []
    if message.elements:
        ingest_lines, query_images = await _handle_uploads(message)
        if ingest_lines:
            await cl.Message(
                content="### Kết quả index\n\n" + "\n\n".join(ingest_lines),
                author="HR Assistant",
            ).send()

    # --- Image search: reverse-image or text+image multimodal query ---
    if query_images:
        await _run_image_search(query_images[0], question)
        return

    if not question:
        if not message.elements:
            await cl.Message(
                content="Vui lòng nhập câu hỏi, đính kèm file tài liệu để index, hoặc gửi ảnh để tìm hình tương tự.",
                author="HR Assistant",
            ).send()
        return

    # --- Intent shortcut: greetings / thanks / small talk bypass RAG ---
    intent = detect_intent(question)
    if intent != Intent.RAG:
        logger.info("[%s] intent=%s -> skip RAG", request_id, intent.value)
        await cl.Message(content=RESPONSES[intent], author="HR Assistant").send()
        return
    logger.info("[%s] intent=rag -> full pipeline", request_id)

    # --- Wait for model warmup if still loading (first query only) ---
    if not _warmup_done.is_set():
        warming_msg = cl.Message(
            content="⏳ Đang nạp model vào GPU (lần đầu)… Sẽ nhanh hơn nhiều ở các câu sau.",
            author="HR Assistant",
        )
        await warming_msg.send()
        await _warmup_models_once()
        warming_msg.content = "✅ Model đã sẵn sàng."
        await warming_msg.update()

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
        logger.info("[%s] search: %d chunks in %d ms",
                    request_id, len(retrieved), stage_timings["search_ms"])
        for i, r in enumerate(retrieved[:5], 1):
            meta = r.get("metadata", {}) or {}
            logger.info("[%s]   retr#%d score=%.3f %s p=%s",
                        request_id, i, r.get("score", 0.0),
                        meta.get("source", "?"), meta.get("page", "?"))

    if not retrieved:
        logger.info("[%s] no retrieval hits -> fallback message", request_id)
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
        logger.info("[%s] rerank: top-%d in %d ms, best=%.3f",
                    request_id, len(reranked), stage_timings["rerank_ms"],
                    reranked[0]["rerank_score"])
        for i, r in enumerate(reranked, 1):
            meta = r.get("metadata", {}) or {}
            logger.info("[%s]   rerank#%d score=%.3f %s p=%s",
                        request_id, i, r.get("rerank_score", 0.0),
                        meta.get("source", "?"), meta.get("page", "?"))

    # --- Generate (streaming) ---
    # Start streaming into the answer message as soon as tokens arrive.
    # This avoids the "blank screen for 60s" feel even on slow hardware.
    answer_msg.content = ""
    answer_parts: list[str] = []
    token_count = 0
    async with cl.Step(name="🧠 Qwen3-8B generate", type="llm") as step:
        prompt = build_prompt(question, reranked)
        step.input = prompt[:1500] + ("..." if len(prompt) > 1500 else "")
        logger.info("[%s] generate: prompt_chars=%d context_chunks=%d",
                    request_id, len(prompt), len(reranked))
        t0 = time.perf_counter()
        first_token_ms: int | None = None
        async for delta in llm.stream(question, reranked):
            if first_token_ms is None:
                first_token_ms = int((time.perf_counter() - t0) * 1000)
                logger.info("[%s] generate: first token after %d ms",
                            request_id, first_token_ms)
            answer_parts.append(delta)
            token_count += 1
            await answer_msg.stream_token(delta)
        stage_timings["generate_ms"] = int((time.perf_counter() - t0) * 1000)
        total_chars = sum(len(p) for p in answer_parts)
        tok_per_sec = (
            token_count / (stage_timings["generate_ms"] / 1000.0)
            if stage_timings["generate_ms"] > 0 else 0.0
        )
        step.output = (
            f"{total_chars} ký tự / ~{token_count} token "
            f"trong {stage_timings['generate_ms']} ms ({tok_per_sec:.1f} tok/s)"
        )
        logger.info(
            "[%s] generate: %d chars, ~%d tok in %d ms (%.1f tok/s, first_token=%s ms)",
            request_id, total_chars, token_count, stage_timings["generate_ms"],
            tok_per_sec, first_token_ms,
        )
        # Warn if speed is suspicious of CPU inference.
        if tok_per_sec and tok_per_sec < 10:
            logger.warning(
                "[%s] generation speed %.1f tok/s is suspiciously low — "
                "model may be running on CPU. Run `ollama ps` or check "
                "OLLAMA_NUM_GPU=-1.",
                request_id, tok_per_sec,
            )
    answer = "".join(answer_parts).strip()

    # --- Source elements (PDF viewer when possible, Text fallback otherwise) ---
    source_elements: list[Any] = []
    source_names: list[str] = []
    for i, chunk in enumerate(reranked, start=1):
        meta = chunk.get("metadata", {}) or {}
        display = _format_source_display(meta, float(chunk.get("rerank_score", 0.0)))
        name = f"[{i}] {display}"
        source_names.append(name)
        source_elements.append(_build_source_element(name, chunk))

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
    logger.info("[%s] --- done total=%d ms (search=%d, rerank=%d, generate=%d)",
                request_id, total_ms,
                stage_timings["search_ms"], stage_timings["rerank_ms"],
                stage_timings["generate_ms"])
