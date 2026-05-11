"""Lightweight intent detection to short-circuit non-RAG messages.

Greetings, thanks, and small talk never need the retrieval pipeline. Detecting
them saves ~1-3 seconds per message (embed + search + rerank + LLM call), and
avoids serving misleading "from documents" answers to trivial inputs.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    THANKS = "thanks"
    GOODBYE = "goodbye"
    SMALL_TALK = "small_talk"
    RAG = "rag"  # default: run the full pipeline


# Keep these patterns tight: false positives (treating a real question as greeting)
# are worse than false negatives (running RAG for a simple hello).
_GREETING_KEYWORDS = {
    "xin chao", "chao", "hello", "hi", "hey", "alo",
    "chao ban", "chao ban", "hi ban", "chao buoi sang",
    "chao buoi chieu", "chao buoi toi", "good morning",
    "good afternoon", "good evening",
}

_THANKS_KEYWORDS = {
    "cam on", "cam on ban", "thanks", "thank you", "tks", "thx", "tnx",
    "cam on nhe", "cam on nhieu", "da cam on", "thank",
}

_GOODBYE_KEYWORDS = {
    "tam biet", "bye", "goodbye", "hen gap lai", "see you", "cya",
}

_SMALL_TALK_KEYWORDS = {
    "ban la ai", "ban ten gi", "ban co the lam gi", "ban lam duoc gi",
    "ban giup duoc gi", "who are you", "what can you do", "help",
    "huong dan", "ban la gi",
}

# Canonical response templates (Vietnamese, professional tone).
RESPONSES: dict[Intent, str] = {
    Intent.GREETING: (
        "Xin chào! Tôi là **Trợ lý tài liệu học tập**. "
        "Bạn có thể hỏi tôi về:\n\n"
        "- Giáo trình, slide, sách tham khảo đã được index\n"
        "- Khái niệm, bài tập, ôn tập (CSDL, CTDL, ML, vi xử lý…)\n"
        "- Tiếng Anh / VSTEP, từ vựng theo chủ đề\n"
        "- Bất kỳ nội dung nào có trong kho tài liệu học tập của bạn\n\n"
        "Hãy đặt câu hỏi cụ thể để tôi tra cứu trong tài liệu nhé."
    ),
    Intent.THANKS: (
        "Rất vui được giúp bạn. Nếu có câu hỏi khác về tài liệu học tập, cứ hỏi nhé."
    ),
    Intent.GOODBYE: (
        "Tạm biệt! Chúc bạn học tập hiệu quả."
    ),
    Intent.SMALL_TALK: (
        "Tôi là **Trợ lý tài liệu học tập** — hỏi đáp dựa trên tài liệu đã được index. "
        "Mọi câu trả lời đều kèm nguồn trích dẫn để bạn kiểm chứng.\n\n"
        "**Một số ví dụ câu hỏi:**\n"
        "- Chuẩn hóa CSDL là gì, các dạng chuẩn 1NF–3NF?\n"
        "- So sánh thuật toán DFS và BFS?\n"
        "- Cấu trúc bài thi VSTEP phần Speaking như thế nào?"
    ),
}


def _normalize(text: str) -> str:
    """Lowercase, strip accents, remove trailing punctuation, collapse whitespace."""
    text = text.strip().lower()
    # Drop trailing/leading punctuation and emoji-like chars.
    text = re.sub(r"[!?.,;:~\-\*_@#$%^&()\[\]{}\"'/\\]+", " ", text)
    # Strip Vietnamese accents for robust matching.
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    # Collapse whitespace.
    return re.sub(r"\s+", " ", stripped).strip()


def detect_intent(message: str, max_chars_for_chitchat: int = 60) -> Intent:
    """Classify a user message.

    Only short messages (default ≤60 chars) are eligible for small-talk
    classification. Longer messages always fall through to RAG — this
    keeps long real questions that happen to start with "Xin chào" from
    being misclassified.
    """
    if not message or not message.strip():
        return Intent.RAG

    norm = _normalize(message)
    if not norm:
        return Intent.RAG

    # Exact-match fast path for very short inputs.
    if len(norm) <= 6:
        tokens = {norm}
    else:
        tokens = {norm}

    # Only apply chit-chat rules for short messages.
    if len(norm) <= max_chars_for_chitchat:
        # Check exact match first.
        if norm in _GREETING_KEYWORDS:
            return Intent.GREETING
        if norm in _THANKS_KEYWORDS:
            return Intent.THANKS
        if norm in _GOODBYE_KEYWORDS:
            return Intent.GOODBYE
        if norm in _SMALL_TALK_KEYWORDS:
            return Intent.SMALL_TALK

        # Prefix match (e.g. "hello there", "cam on nhieu nhe").
        for kw in _GREETING_KEYWORDS:
            if norm == kw or norm.startswith(kw + " "):
                return Intent.GREETING
        for kw in _THANKS_KEYWORDS:
            if norm == kw or norm.startswith(kw + " ") or norm.endswith(" " + kw):
                return Intent.THANKS
        for kw in _GOODBYE_KEYWORDS:
            if norm == kw or norm.startswith(kw + " "):
                return Intent.GOODBYE
        for kw in _SMALL_TALK_KEYWORDS:
            if kw in norm:
                return Intent.SMALL_TALK

    return Intent.RAG
