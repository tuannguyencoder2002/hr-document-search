"""Retrieve images from the CLIP-indexed collection, given a query image or text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient

from src.config import get_settings
from src.ingestion.image_indexer import IMAGE_VECTOR_NAME
from src.search.clip_embedder import CLIPEmbedder
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageRetriever:
    """Query the image collection with either a user image or a text description.

    Both modalities live in the same 512-d CLIP space, so cosine similarity
    works across them without extra calibration.
    """

    def __init__(
        self,
        client: QdrantClient | None = None,
        clip: CLIPEmbedder | None = None,
        collection: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or settings.create_qdrant_client()
        self.clip = clip or CLIPEmbedder()
        self.collection = collection or settings.image_collection
        self.default_top_k = settings.image_top_k

    def search_by_image(
        self,
        image_path: str | Path,
        limit: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Reverse image search: encode user image, return similar images in corpus."""
        k = limit or self.default_top_k
        vec = self.clip.encode_image(image_path)[0].tolist()
        return self._query(vec, k, score_threshold)

    def search_by_text(
        self,
        query: str,
        limit: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Text-to-image: encode text, return semantically matching images."""
        if not query.strip():
            return []
        k = limit or self.default_top_k
        vec = self.clip.encode_text(query)[0].tolist()
        return self._query(vec, k, score_threshold)

    def _query(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float | None,
    ) -> list[dict[str, Any]]:
        hits = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            using=IMAGE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold,
        ).points

        results: list[dict[str, Any]] = []
        for hit in hits:
            payload = hit.payload or {}
            meta = payload.get("metadata", {}) or {}
            results.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "metadata": meta,
                    "image_path": meta.get("image_path"),
                }
            )
        return results
