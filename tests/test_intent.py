"""Unit tests for intent detection (greeting shortcut)."""

from __future__ import annotations

import pytest

from src.generation.intent import Intent, detect_intent


@pytest.mark.parametrize(
    "text",
    [
        "xin chào",
        "Xin chào!",
        "chào bạn",
        "Chào",
        "hello",
        "Hi",
        "hey",
        "Chào buổi sáng",
        "alo",
    ],
)
def test_greetings_detected(text: str):
    assert detect_intent(text) == Intent.GREETING


@pytest.mark.parametrize(
    "text",
    [
        "cảm ơn",
        "Cảm ơn bạn",
        "cảm ơn nhiều nhé",
        "thanks",
        "thank you",
        "tks",
    ],
)
def test_thanks_detected(text: str):
    assert detect_intent(text) == Intent.THANKS


@pytest.mark.parametrize(
    "text",
    [
        "tạm biệt",
        "bye",
        "goodbye",
        "hẹn gặp lại",
    ],
)
def test_goodbye_detected(text: str):
    assert detect_intent(text) == Intent.GOODBYE


@pytest.mark.parametrize(
    "text",
    [
        "bạn là ai",
        "Bạn là ai?",
        "bạn có thể làm gì",
        "who are you",
    ],
)
def test_small_talk_detected(text: str):
    assert detect_intent(text) == Intent.SMALL_TALK


@pytest.mark.parametrize(
    "text",
    [
        "Nhân viên được nghỉ phép bao nhiêu ngày?",
        "Lương thử việc bằng bao nhiêu phần trăm?",
        "Quy trình xin nghỉ việc gồm những bước nào?",
        "Chính sách làm việc từ xa",
        "Mức lương tối thiểu năm 2025 là bao nhiêu?",
        # Real question that starts with a greeting word must NOT be misclassified.
        "Chào bạn, cho tôi hỏi chính sách nghỉ phép như thế nào và có được cộng dồn không?",
    ],
)
def test_real_questions_go_to_rag(text: str):
    assert detect_intent(text) == Intent.RAG


def test_empty_input_returns_rag():
    assert detect_intent("") == Intent.RAG
    assert detect_intent("   ") == Intent.RAG


def test_trailing_punctuation_ignored():
    assert detect_intent("chào!!!") == Intent.GREETING
    assert detect_intent("cảm ơn...") == Intent.THANKS
