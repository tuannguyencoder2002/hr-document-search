"""Extract and index images from all documents in a folder.

This is a standalone script that ONLY processes images (CLIP encoding +
Qdrant upsert into the `hr_images` collection). It does NOT re-embed text.

Use this when:
  - You already ingested text but images were skipped (CLIP wasn't cached).
  - You want to rebuild the image index without touching text chunks.
"""

from __future__ import annotations

import src.hf_offline  # noqa: F401

import argparse
from pathlib import Path

from src.config import get_settings
from src.ingestion.image_extractor import extract_images
from src.ingestion.image_indexer import ImageIndexer
from src.ingestion.manifest import Manifest, sha256_of_file
from src.utils.logger import get_logger, setup_logging

SUPPORTED = {".pdf", ".docx"}


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    parser = argparse.ArgumentParser(description="Extract + index images from documents.")
    parser.add_argument("--folder", type=str, required=True)
    parser.add_argument("--top-k-test", type=int, default=0, help="If >0, run a test query after indexing.")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")

    files = sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED
    )
    if not files:
        logger.warning("No PDF/DOCX files in %s", folder)
        return

    settings = get_settings()
    indexer = ImageIndexer()
    total_images = 0

    for f in files:
        logger.info("Extracting images from %s", f.name)
        doc_id = f"doc_{sha256_of_file(f)[:10]}"
        try:
            summary = indexer.ingest_file(f, document_id=doc_id)
            n = summary.get("images_indexed", 0)
            total_images += n
            if n > 0:
                logger.info("  → %d images indexed", n)
        except Exception as e:
            logger.warning("  → failed: %s", e)

    logger.info("Done. %d files processed, %d images indexed total.", len(files), total_images)

    if args.top_k_test > 0 and total_images > 0:
        from src.search.image_retriever import ImageRetriever

        retriever = ImageRetriever()
        # Quick sanity: text-to-image search.
        hits = retriever.search_by_text("diagram", limit=args.top_k_test)
        logger.info("Test query 'diagram': %d hits", len(hits))
        for h in hits:
            meta = h.get("metadata", {})
            logger.info("  score=%.3f %s p=%s", h["score"], meta.get("source"), meta.get("page"))


if __name__ == "__main__":
    main()
