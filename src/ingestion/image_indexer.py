"""Extract images from a file and index them into a dedicated Qdrant collection.

Collection layout (dense-only, no sparse):
  vector "image": CLIP image embedding (512-d, cosine)
  payload: { source, source_path, page, figure_index, caption, image_path,
             width, height, document_id, file_type }

For text->image search you simply encode the query with CLIPEmbedder.encode_text
and query this collection using the same vector name — embeddings share the
same 512-d space.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from tqdm import tqdm

from src.config import get_settings
from src.ingestion.image_extractor import ExtractedImage, extract_images
from src.search.clip_embedder import CLIPEmbedder
from src.utils.logger import get_logger

logger = get_logger(__name__)

IMAGE_VECTOR_NAME = "image"


def ensure_image_collection(
    client: QdrantClient,
    name: str,
    vector_size: int,
) -> None:
    """Create the image collection if it doesn't exist."""
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config={
            IMAGE_VECTOR_NAME: qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
        },
    )
    logger.info("Created Qdrant image collection: %s", name)


class ImageIndexer:
    """Extract images from a document, encode with CLIP, upsert to Qdrant."""

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
        self.vector_size = settings.clip_vector_size
        ensure_image_collection(self.client, self.collection, self.vector_size)

    def _upsert_batch(
        self,
        images: list[ExtractedImage],
        document_id: str,
        batch_size: int = 8,
    ) -> int:
        total = 0
        for start in tqdm(range(0, len(images), batch_size), desc="CLIP encoding images"):
            batch = images[start : start + batch_size]
            embeds = self.clip.encode_image([img.image_path for img in batch], batch_size=batch_size)
            points: list[qm.PointStruct] = []
            for i, img in enumerate(batch):
                meta = dict(img.metadata)
                meta.update(
                    {
                        "image_path": str(img.image_path),
                        "width": img.width,
                        "height": img.height,
                        "document_id": document_id,
                    }
                )
                points.append(
                    qm.PointStruct(
                        id=str(uuid.uuid4()),
                        vector={IMAGE_VECTOR_NAME: embeds[i].tolist()},
                        payload={"metadata": meta, "document_id": document_id},
                    )
                )
            self.client.upsert(collection_name=self.collection, points=points)
            total += len(points)
        return total

    def ingest_file(
        self,
        file_path: str | Path,
        document_id: str,
        extra_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract + index all images from a file. Returns summary dict."""
        path = Path(file_path)
        images = extract_images(path)
        if extra_meta:
            for img in images:
                img.metadata.update(extra_meta)
        if not images:
            return {"document_id": document_id, "images_indexed": 0}
        n = self._upsert_batch(images, document_id=document_id)
        logger.info("Indexed %d images from %s", n, path.name)
        return {"document_id": document_id, "images_indexed": n}

    def delete_document(self, document_id: str) -> None:
        """Remove all image points that belong to a document_id."""
        flt = qm.Filter(
            must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
        )
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(filter=flt),
        )
