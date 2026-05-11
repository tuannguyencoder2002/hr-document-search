"""Embed chunks and upsert them into Qdrant."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from tqdm import tqdm

from src.config import get_settings
from src.ingestion.chunker import Chunk, chunk_documents
from src.ingestion.cleaner import clean_text
from src.ingestion.parser import parse_file
from src.search.embedder import BGEEmbedder
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.ingestion.manifest import Manifest

logger = get_logger(__name__)


def ensure_collection(client: QdrantClient, name: str, dense_size: int) -> None:
    """Create Qdrant collection with dense + sparse vector configs if missing."""
    settings = get_settings()
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config={
            settings.qdrant_dense_name: qm.VectorParams(
                size=dense_size, distance=qm.Distance.COSINE
            ),
        },
        sparse_vectors_config={
            settings.qdrant_sparse_name: qm.SparseVectorParams(
                index=qm.SparseIndexParams(on_disk=False),
            ),
        },
    )
    logger.info("Created Qdrant collection: %s", name)


class Indexer:
    """Ingest files: parse -> clean -> chunk -> embed -> upsert to Qdrant."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        embedder: BGEEmbedder | None = None,
        collection: str | None = None,
        image_indexer: Any = None,
    ) -> None:
        settings = get_settings()
        self.client = client or settings.create_qdrant_client()
        self.embedder = embedder or BGEEmbedder()
        self.collection = collection or settings.qdrant_collection
        self.dense_name = settings.qdrant_dense_name
        self.sparse_name = settings.qdrant_sparse_name
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        ensure_collection(self.client, self.collection, settings.qdrant_dense_size)

        # Optional image indexer: lazy-initialized unless explicitly passed in.
        self._image_indexer = image_indexer
        self._image_search_enabled = settings.image_search_enabled

    def _get_image_indexer(self) -> Any | None:
        """Lazily build an ImageIndexer the first time we need one."""
        if not self._image_search_enabled:
            return None
        if self._image_indexer is None:
            try:
                from src.ingestion.image_indexer import ImageIndexer

                self._image_indexer = ImageIndexer(client=self.client)
            except Exception as e:
                logger.warning("Image indexing unavailable, continuing text-only: %s", e)
                self._image_search_enabled = False
                return None
        return self._image_indexer

    def _prepare_chunks(self, file_path: str | Path, extra_meta: dict[str, Any] | None) -> list[Chunk]:
        docs = parse_file(file_path)
        for d in docs:
            d.text = clean_text(d.text)
            if extra_meta:
                d.metadata.update(extra_meta)
        docs = [d for d in docs if d.text]
        return chunk_documents(docs, chunk_size=self.chunk_size, overlap=self.chunk_overlap)

    def _upsert_batch(self, chunks: list[Chunk], document_id: str, batch_size: int = 16) -> int:
        total = 0
        for start in tqdm(range(0, len(chunks), batch_size), desc="Embedding"):
            batch = chunks[start : start + batch_size]
            texts = [c.text for c in batch]
            enc = self.embedder.encode_batch(texts, batch_size=batch_size)
            dense_matrix = enc["dense"]
            sparse_list = enc["sparse"]

            points: list[qm.PointStruct] = []
            for i, chunk in enumerate(batch):
                point_id = str(uuid.uuid4())
                meta = dict(chunk.metadata)
                meta["document_id"] = document_id
                sparse_raw = sparse_list[i]
                sparse_vec = qm.SparseVector(
                    indices=list(sparse_raw.keys()),
                    values=list(sparse_raw.values()),
                )
                points.append(
                    qm.PointStruct(
                        id=point_id,
                        vector={
                            self.dense_name: dense_matrix[i].tolist(),
                            self.sparse_name: sparse_vec,
                        },
                        payload={
                            "text": chunk.text,
                            "metadata": meta,
                            "document_id": document_id,
                        },
                    )
                )
            self.client.upsert(collection_name=self.collection, points=points)
            total += len(points)
        return total

    def ingest_file(
        self,
        file_path: str | Path,
        extra_meta: dict[str, Any] | None = None,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a single file and return a summary dict."""
        path = Path(file_path)
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:10]}"
        chunks = self._prepare_chunks(path, extra_meta)
        if not chunks:
            logger.warning("No content extracted from %s", path)
            return {
                "document_id": doc_id,
                "filename": path.name,
                "pages": 0,
                "chunks_indexed": 0,
                "images_indexed": 0,
            }
        n = self._upsert_batch(chunks, document_id=doc_id)
        pages = len({c.metadata.get("page") for c in chunks})

        # Index images (best-effort, doesn't fail the text ingest if it errors).
        images_indexed = 0
        img_idx = self._get_image_indexer()
        if img_idx is not None:
            try:
                summary = img_idx.ingest_file(
                    path,
                    document_id=doc_id,
                    extra_meta=extra_meta or {},
                )
                images_indexed = summary.get("images_indexed", 0)
            except Exception as e:
                logger.warning("Image indexing failed for %s: %s", path.name, e)

        logger.info(
            "Indexed %s: %d chunks across %d pages, %d images",
            path.name, n, pages, images_indexed,
        )
        return {
            "document_id": doc_id,
            "filename": path.name,
            "pages": pages,
            "chunks_indexed": n,
            "images_indexed": images_indexed,
        }

    def ingest_file_incremental(
        self,
        file_path: str | Path,
        manifest: "Manifest",
        extra_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest with manifest-based deduplication.

        - If manifest has this file at the same sha256 -> skip entirely.
        - If manifest has this file with a different hash -> delete old chunks,
          reindex with the same document_id so references stay stable.
        - Otherwise -> fresh ingest and record in manifest.

        The caller is responsible for calling `manifest.save()` afterwards
        (e.g. once per batch) to avoid excessive disk writes.
        """
        from src.ingestion.manifest import Manifest, sha256_of_file  # local import to avoid cycle

        path = Path(file_path)
        sha = sha256_of_file(path)

        existing = manifest.get(path)
        if existing is not None and existing.sha256 == sha:
            logger.info("Unchanged, skipping: %s", path.name)
            return {
                "document_id": existing.document_id,
                "filename": path.name,
                "pages": 0,
                "chunks_indexed": 0,
                "status": "unchanged",
            }

        doc_id = existing.document_id if existing is not None else f"doc_{uuid.uuid4().hex[:10]}"
        if existing is not None:
            logger.info("Content changed, re-indexing: %s", path.name)
            try:
                self.delete_document(doc_id)
            except Exception as e:
                logger.warning("Could not delete old chunks for %s: %s", doc_id, e)

        summary = self.ingest_file(path, extra_meta=extra_meta, document_id=doc_id)
        if summary["chunks_indexed"] > 0:
            manifest.update(
                path=path,
                sha256=sha,
                document_id=doc_id,
                chunks_indexed=summary["chunks_indexed"],
            )
            summary["status"] = "reindexed" if existing is not None else "indexed"
        else:
            summary["status"] = "empty"
        return summary

    def delete_file(
        self,
        file_path: str | Path,
        manifest: "Manifest",
    ) -> bool:
        """Delete a file's chunks from Qdrant and drop it from manifest.

        Returns True if the file was found and removed, False otherwise.
        """
        path = Path(file_path)
        rec = manifest.get(path)
        if rec is None:
            return False
        try:
            self.delete_document(rec.document_id)
        except Exception as e:
            logger.warning("Delete failed for %s: %s", rec.document_id, e)
        manifest.remove(path)
        return True

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document_id."""
        flt = qm.Filter(
            must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
        )
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(filter=flt),
        )
        # Also clean up associated images if that indexer is available.
        img_idx = self._get_image_indexer()
        if img_idx is not None:
            try:
                img_idx.delete_document(document_id)
            except Exception as e:
                logger.warning("Image delete failed for %s: %s", document_id, e)
        return 1

    def list_documents(self) -> list[dict[str, Any]]:
        """Return aggregate info about indexed documents."""
        offset = None
        docs: dict[str, dict[str, Any]] = {}
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                payload = p.payload or {}
                doc_id = payload.get("document_id")
                meta = payload.get("metadata", {})
                if not doc_id:
                    continue
                entry = docs.setdefault(
                    doc_id,
                    {
                        "document_id": doc_id,
                        "filename": meta.get("source", ""),
                        "doc_type": meta.get("doc_type"),
                        "department": meta.get("department"),
                        "pages": set(),
                        "chunks_count": 0,
                    },
                )
                entry["chunks_count"] += 1
                if meta.get("page") is not None:
                    entry["pages"].add(meta["page"])
            if offset is None:
                break
        for entry in docs.values():
            entry["pages"] = len(entry["pages"])
        return list(docs.values())
