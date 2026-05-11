"""Embed chunks and upsert them into Qdrant."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from tqdm import tqdm

from src.config import get_settings
from src.ingestion.chunker import Chunk, chunk_documents
from src.ingestion.cleaner import clean_text
from src.ingestion.parser import parse_file
from src.search.embedder import BGEEmbedder
from src.utils.logger import get_logger

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
            }
        n = self._upsert_batch(chunks, document_id=doc_id)
        pages = len({c.metadata.get("page") for c in chunks})
        logger.info("Indexed %s: %d chunks across %d pages", path.name, n, pages)
        return {
            "document_id": doc_id,
            "filename": path.name,
            "pages": pages,
            "chunks_indexed": n,
        }

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document_id."""
        flt = qm.Filter(
            must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
        )
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(filter=flt),
        )
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
