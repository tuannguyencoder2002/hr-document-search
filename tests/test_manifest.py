"""Unit tests for the ingest manifest."""

from __future__ import annotations

from pathlib import Path

from src.ingestion.manifest import Manifest, sha256_of_file


def test_sha256_of_file_stable(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello world")
    h1 = sha256_of_file(f)
    h2 = sha256_of_file(f)
    assert h1 == h2
    assert len(h1) == 64


def test_sha256_changes_on_content_change(tmp_path: Path):
    f = tmp_path / "b.txt"
    f.write_bytes(b"v1")
    h1 = sha256_of_file(f)
    f.write_bytes(b"v2")
    h2 = sha256_of_file(f)
    assert h1 != h2


def test_manifest_roundtrip(tmp_path: Path):
    mpath = tmp_path / "m.json"
    m = Manifest(path=mpath)
    assert len(m) == 0

    target = tmp_path / "doc.txt"
    target.write_text("content", encoding="utf-8")
    sha = sha256_of_file(target)
    m.update(target, sha=sha, document_id="doc_123", chunks_indexed=5)
    m.save()

    # Reload from disk.
    m2 = Manifest(path=mpath)
    assert len(m2) == 1
    rec = m2.get(target)
    assert rec is not None
    assert rec.sha256 == sha
    assert rec.document_id == "doc_123"
    assert rec.chunks_indexed == 5


def test_manifest_is_up_to_date(tmp_path: Path):
    m = Manifest(path=tmp_path / "m.json")
    f = tmp_path / "x.txt"
    f.write_bytes(b"hello")
    sha = sha256_of_file(f)
    assert not m.is_up_to_date(f, sha)
    m.update(f, sha=sha, document_id="d1", chunks_indexed=1)
    assert m.is_up_to_date(f, sha)
    # After content change, manifest is stale.
    f.write_bytes(b"hello-changed")
    new_sha = sha256_of_file(f)
    assert not m.is_up_to_date(f, new_sha)


def test_manifest_remove(tmp_path: Path):
    m = Manifest(path=tmp_path / "m.json")
    f = tmp_path / "x.txt"
    f.write_bytes(b"data")
    sha = sha256_of_file(f)
    m.update(f, sha=sha, document_id="d", chunks_indexed=1)
    assert m.get(f) is not None
    m.remove(f)
    assert m.get(f) is None


def test_manifest_handles_corrupt_file(tmp_path: Path):
    mpath = tmp_path / "m.json"
    mpath.write_text("{ this is not json", encoding="utf-8")
    m = Manifest(path=mpath)
    assert len(m) == 0


def test_update_keyed_by_absolute_path(tmp_path: Path):
    mpath = tmp_path / "m.json"
    m = Manifest(path=mpath)
    f = tmp_path / "doc.txt"
    f.write_text("x", encoding="utf-8")
    sha = sha256_of_file(f)
    m.update(f, sha=sha, document_id="d", chunks_indexed=1)
    # Same file via a different (non-resolved) Path instance must hit the same record.
    other = Path(str(f))
    assert m.get(other) is not None
