"""Persistent manifest of files already ingested, for incremental ingestion.

File path -> {
    "sha256": "...",
    "mtime": 1700000000.0,
    "size": 12345,
    "document_id": "doc_abcdef",
    "chunks_indexed": 142,
    "indexed_at": "2025-01-15T10:30:00"
}

Lookup key is the **absolute, resolved** file path (str). Saved alongside the
Qdrant data at `<qdrant_local_path>/ingest_manifest.json` by default, or at any
path you pass to `Manifest(path=...)`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileRecord:
    sha256: str
    mtime: float
    size: int
    document_id: str
    chunks_indexed: int
    indexed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "mtime": self.mtime,
            "size": self.size,
            "document_id": self.document_id,
            "chunks_indexed": self.chunks_indexed,
            "indexed_at": self.indexed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FileRecord:
        return cls(
            sha256=d["sha256"],
            mtime=float(d.get("mtime", 0.0)),
            size=int(d.get("size", 0)),
            document_id=d["document_id"],
            chunks_indexed=int(d.get("chunks_indexed", 0)),
            indexed_at=d.get("indexed_at", ""),
        )


def sha256_of_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Stream SHA256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            buf = fp.read(chunk_size)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


class Manifest:
    """JSON-backed manifest keyed by resolved absolute path."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            settings = get_settings()
            base = Path(settings.resolved_qdrant_local_path())
            base.mkdir(parents=True, exist_ok=True)
            path = base / "ingest_manifest.json"
        self.path = Path(path)
        self._records: dict[str, FileRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read manifest %s: %s — starting fresh", self.path, e)
            return
        for key, value in (raw.get("files") or {}).items():
            try:
                self._records[key] = FileRecord.from_dict(value)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Skipping malformed manifest entry %s: %s", key, e)

    def save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        data = {
            "version": 1,
            "files": {k: v.to_dict() for k, v in self._records.items()},
        }
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _key(path: Path) -> str:
        return str(path.resolve())

    def get(self, path: Path) -> FileRecord | None:
        return self._records.get(self._key(path))

    def is_up_to_date(self, path: Path, sha256: str) -> bool:
        """True if the manifest already has this file at the same hash."""
        rec = self.get(path)
        return rec is not None and rec.sha256 == sha256

    def update(
        self,
        path: Path,
        sha256: str,
        document_id: str,
        chunks_indexed: int,
    ) -> FileRecord:
        stat = path.stat()
        rec = FileRecord(
            sha256=sha256,
            mtime=stat.st_mtime,
            size=stat.st_size,
            document_id=document_id,
            chunks_indexed=chunks_indexed,
            indexed_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._records[self._key(path)] = rec
        return rec

    def remove(self, path: Path) -> FileRecord | None:
        return self._records.pop(self._key(path), None)

    def items(self) -> list[tuple[str, FileRecord]]:
        return list(self._records.items())

    def __len__(self) -> int:
        return len(self._records)
