"""Hybrid retrieval: dense ANN + sparse search over Qdrant, fused with RRF."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from src.config import get_settings, get_shared_qdrant_client
from src.search.embedder import BGEEmbedder
from src.utils.logger import get_logger

logger = get_logger(__name__)


def rrf_fusion(
    ranked_lists: list[list[tuple[str, int]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion.

    Each input list is [(doc_id, rank_index_0_based), ...].
    Returns [(doc_id, score), ...] sorted by score desc.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for doc_id, rank in ranked:
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    """Hybrid retrieval over a Qdrant collection with dense + sparse vectors."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        embedder: BGEEmbedder | None = None,
        collection: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or get_shared_qdrant_client()
        self.embedder = embedder or BGEEmbedder()
        self.collection = collection or settings.qdrant_collection
        self.dense_name = settings.qdrant_dense_name
        self.sparse_name = settings.qdrant_sparse_name
        self.rrf_k = settings.rrf_k

    def _build_filter(self, filter_dict: dict[str, Any] | None) -> qm.Filter | None:
        if not filter_dict:
            return None
        must = []
        for key, value in filter_dict.items():
            must.append(
                qm.FieldCondition(key=key, match=qm.MatchValue(value=value))
            )
        return qm.Filter(must=must)

    def search(
        self,
        query: str,
        limit: int = 30,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run hybrid search and return fused results."""
        enc = self.embedder.encode(query)
        dense_vec = enc["dense"].tolist()
        sparse_raw = enc["sparse"]
        sparse_vec = qm.SparseVector(
            indices=list(sparse_raw.keys()),
            values=list(sparse_raw.values()),
        )

        qdrant_filter = self._build_filter(filter)

        # Use the query_points batch API so we get the best of both worlds in one RTT.
        requests = [
            qm.QueryRequest(
                query=dense_vec,
                using=self.dense_name,
                limit=limit,
                with_payload=True,
                filter=qdrant_filter,
            ),
            qm.QueryRequest(
                query=sparse_vec,
                using=self.sparse_name,
                limit=limit,
                with_payload=True,
                filter=qdrant_filter,
            ),
        ]
        responses = self.client.query_batch_points(
            collection_name=self.collection,
            requests=requests,
        )
        dense_hits = responses[0].points
        sparse_hits = responses[1].points

        by_id: dict[str, Any] = {}
        dense_rank = []
        sparse_rank = []
        for rank, hit in enumerate(dense_hits):
            doc_id = str(hit.id)
            dense_rank.append((doc_id, rank))
            by_id[doc_id] = hit
        for rank, hit in enumerate(sparse_hits):
            doc_id = str(hit.id)
            sparse_rank.append((doc_id, rank))
            by_id.setdefault(doc_id, hit)

        fused = rrf_fusion([dense_rank, sparse_rank], k=self.rrf_k)

        results: list[dict[str, Any]] = []
        for doc_id, score in fused[:limit]:
            hit = by_id[doc_id]
            payload = hit.payload or {}
            results.append(
                {
                    "id": doc_id,
                    "score": float(score),
                    "text": payload.get("text", ""),
                    "metadata": payload.get("metadata", {}),
                }
            )
        return results
