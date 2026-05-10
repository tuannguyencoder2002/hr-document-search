"""RAG prompt templates."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = (
    "Bạn là trợ lý AI của bộ phận Nhân sự, chuyên trả lời câu hỏi về chính sách, "
    "quy trình và quy định của công ty dựa trên tài liệu được cung cấp."
)

RAG_PROMPT = """QUY TẮC:
1. Chỉ trả lời dựa trên thông tin trong [TÀI LIỆU] bên dưới.
2. Nếu tài liệu không chứa câu trả lời, nói rõ: "Tài liệu hiện tại không có thông tin về vấn đề này. Vui lòng liên hệ bộ phận HR để được hỗ trợ."
3. Luôn trích dẫn nguồn ở cuối mỗi ý: [Tên file, Trang X]
4. Trả lời ngắn gọn, rõ ràng (3-5 câu).
5. Ngôn ngữ: tiếng Việt, trang trọng nhưng thân thiện.

[TÀI LIỆU]:
{context}

[CÂU HỎI]:
{question}

[TRẢ LỜI]:"""


def format_context(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunks into a numbered context string with citations."""
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        meta = c.get("metadata", {}) or {}
        source = meta.get("source", "unknown")
        page = meta.get("page", "?")
        text = c.get("text", "").strip()
        lines.append(f"[{i}] [{source}, Trang {page}]\n{text}")
    return "\n\n".join(lines)


def build_prompt(question: str, chunks: list[dict[str, Any]]) -> str:
    """Build the final RAG prompt."""
    context = format_context(chunks) if chunks else "(không có tài liệu liên quan)"
    return RAG_PROMPT.format(context=context, question=question.strip())
