"""Batch ingest all supported files under a folder."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ingestion.indexer import Indexer
from src.utils.logger import get_logger, setup_logging

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    parser = argparse.ArgumentParser(description="Batch ingest HR documents into Qdrant.")
    parser.add_argument("--folder", type=str, required=True, help="Folder containing documents.")
    parser.add_argument("--doc-type", type=str, default=None)
    parser.add_argument("--department", type=str, default=None)
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]
    if not files:
        logger.warning("No supported files in %s", folder)
        return

    indexer = Indexer()
    total_chunks = 0
    extra: dict = {}
    if args.doc_type:
        extra["doc_type"] = args.doc_type
    if args.department:
        extra["department"] = args.department

    ok_files = 0
    failed = 0
    for f in files:
        logger.info("Ingesting %s", f)
        try:
            summary = indexer.ingest_file(f, extra_meta=dict(extra))
            total_chunks += summary["chunks_indexed"]
            ok_files += 1
        except Exception as e:
            failed += 1
            logger.exception("Failed to ingest %s: %s", f, e)

    logger.info(
        "Done. %d/%d files OK, %d failed, %d chunks total.",
        ok_files,
        len(files),
        failed,
        total_chunks,
    )


if __name__ == "__main__":
    main()
