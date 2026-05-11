"""Unit tests for file parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.parser import parse_file, parse_pdf, parse_txt


def test_parse_empty_pdf_returns_empty(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("Nhân viên được nghỉ 12 ngày.", encoding="utf-8")
    docs = parse_txt(f)
    assert len(docs) == 1
    assert "Nhân viên" in docs[0].text
    assert docs[0].metadata["source"] == "hello.txt"
    assert docs[0].metadata["file_type"] == "txt"


def test_parse_empty_txt_returns_empty(tmp_path: Path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    assert parse_txt(f) == []


def test_parse_empty_pdf_returns_empty(tmp_path: Path):
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"")
    assert parse_pdf(f) == []


def test_parse_missing_file_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        parse_file(tmp_path / "nope.pdf")


def test_parse_unsupported_extension(tmp_path: Path):
    f = tmp_path / "weird.xyz"
    f.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_file(f)


def test_parse_file_dispatches_to_txt(tmp_path: Path):
    f = tmp_path / "note.txt"
    f.write_text("hello", encoding="utf-8")
    docs = parse_file(f)
    assert len(docs) == 1
    assert docs[0].text == "hello"
