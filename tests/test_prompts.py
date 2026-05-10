"""Unit tests for prompt building."""

from __future__ import annotations

from src.generation.prompts import build_prompt, format_context


def test_format_context_empty():
    assert format_context([]) == ""


def test_format_context_includes_citation_and_text():
    chunks = [
        {"text": "Nhân viên được nghỉ 12 ngày.", "metadata": {"source": "a.pdf", "page": 12}},
        {"text": "Lương thử việc 85%.", "metadata": {"source": "b.docx", "page": 5}},
    ]
    ctx = format_context(chunks)
    assert "[a.pdf, Trang 12]" in ctx
    assert "[b.docx, Trang 5]" in ctx
    assert "Nhân viên được nghỉ 12 ngày." in ctx
    assert "Lương thử việc 85%." in ctx


def test_build_prompt_includes_question_and_context():
    prompt = build_prompt(
        "Nghỉ phép bao nhiêu?",
        [{"text": "12 ngày.", "metadata": {"source": "a.pdf", "page": 1}}],
    )
    assert "Nghỉ phép bao nhiêu?" in prompt
    assert "12 ngày." in prompt
    assert "QUY TẮC" in prompt
    assert "[TÀI LIỆU]" in prompt


def test_build_prompt_without_chunks_uses_placeholder():
    prompt = build_prompt("Q?", [])
    assert "không có tài liệu liên quan" in prompt
