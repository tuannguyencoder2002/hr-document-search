"""Batch ingest all supported files under a folder — incremental by default.

On each run:
  * new files             -> index
  * files with same hash  -> skip (no re-embed)
  * files with new hash   -> re-index in-place
  * files removed on disk -> optionally purge from Qdrant with --prune

This lets you drop a new PDF into your folder and only pay the embedding cost
for that one file, not the whole corpus.
"""

from __future__ import annotations

import src.hf_offline  # noqa: F401  # must be first

import argparse
from pathlib import Path

from src.ingestion.indexer import Indexer
from src.ingestion.manifest import Manifest
from src.utils.logger import get_logger, setup_logging

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    parser = argparse.ArgumentParser(description="Incremental ingest of documents into Qdrant.")
    parser.add_argument("--folder", type=str, required=True, help="Folder containing documents.")
    parser.add_argument("--doc-type", type=str, default=None)
    parser.add_argument("--department", type=str, default=None)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Ignore manifest and re-embed every file (WARNING: slow).",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete chunks for files that exist in manifest but not on disk.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Override manifest path (default: <qdrant_local_path>/ingest_manifest.json).",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    files = sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED
    )
    if not files:
        logger.warning("No supported files in %s", folder)
        return

    indexer = Indexer()
    manifest = Manifest(path=args.manifest)

    extra: dict = {}
    if args.doc_type:
        extra["doc_type"] = args.doc_type
    if args.department:
        extra["department"] = args.department

    # --- Purge entries for files removed from disk ---
    if args.prune:
        disk_keys = {str(f.resolve()) for f in files}
        stale = [k for k, _ in manifest.items() if k not in disk_keys]
        for key in stale:
            try:
                indexer.delete_file(Path(key), manifest)
                logger.info("Pruned missing file from index: %s", key)
            except Exception as e:
                logger.warning("Prune failed for %s: %s", key, e)

    # --- Ingest each file (incremental or forced rebuild) ---
    stats = {"indexed": 0, "reindexed": 0, "unchanged": 0, "failed": 0, "empty": 0}
    total_chunks = 0

    for f in files:
        try:
            if args.rebuild:
                # Drop existing manifest entry so it's treated as fresh.
                manifest.remove(f)
            summary = indexer.ingest_file_incremental(
                f,
                manifest=manifest,
                extra_meta=dict(extra),
            )
            status = summary.get("status", "indexed")
            stats[status] = stats.get(status, 0) + 1
            total_chunks += summary.get("chunks_indexed", 0)
            logger.info(
                "[%s] %s — %d chunks (doc_id=%s)",
                status,
                f.name,
                summary.get("chunks_indexed", 0),
                summary.get("document_id", "?"),
            )
        except Exception as e:
            stats["failed"] += 1
            logger.exception("Failed to ingest %s: %s", f, e)

    manifest.save()

    logger.info(
        "Done. indexed=%d, reindexed=%d, unchanged=%d, empty=%d, failed=%d | new chunks=%d | manifest=%s",
        stats["indexed"],
        stats["reindexed"],
        stats["unchanged"],
        stats["empty"],
        stats["failed"],
        total_chunks,
        manifest.path,
    )


if __name__ == "__main__":
    main()
