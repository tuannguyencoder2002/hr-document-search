"""Unit tests for Vietnamese text cleaner."""

from __future__ import annotations

import unicodedata

from src.ingestion.cleaner import clean_text


def test_clean_empty_returns_empty():
    assert clean_text("") == ""
    assert clean_text("   ") == ""


def test_clean_preserves_vietnamese():
    text = "Nhân viên được nghỉ 12 ngày phép/năm."
    out = clean_text(text)
    assert "Nhân viên" in out
    assert "nghỉ" in out


def test_clean_normalizes_to_nfc():
    # Decomposed form of "Nhân" (N + h + a + combining circumflex + n).
    nfd = unicodedata.normalize("NFD", "Nhân viên")
    out = clean_text(nfd)
    assert out == unicodedata.normalize("NFC", out)
    assert "Nhân" in out


def test_clean_removes_control_chars():
    text = "Hello\x00World\x07!"
    out = clean_text(text)
    assert "\x00" not in out
    assert "\x07" not in out
    assert "HelloWorld!" == out


def test_clean_collapses_horizontal_whitespace():
    text = "Hello    World\t\tfoo"
    out = clean_text(text)
    assert out == "Hello World foo"


def test_clean_preserves_paragraph_breaks_but_collapses_runs():
    text = "Para 1.\n\n\n\nPara 2."
    out = clean_text(text)
    assert "Para 1." in out
    assert "Para 2." in out
    assert "\n\n\n" not in out
