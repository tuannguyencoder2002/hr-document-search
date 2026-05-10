"""Cross-encoder reranker using bge-reranker-v2-m3."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Lazy-loaded cross-encoder reranker."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        use_fp16: bool = True,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.reranker_model
        self.device = device or settings.resolved_device()
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self._model = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            from FlagEmbedding import FlagReranker

            logger.info(
                "Loading reranker %s on %s (fp16=%s)",
                self.model_name,
                self.device,
                self.use_fp16,
            )
            try:
                self._model = FlagReranker(
                    self.model_name,
                    use_fp16=self.use_fp16,
                    devices=self.device,
                )
            except TypeError:
                self._model = FlagReranker(
                    self.model_name,
                    use_fp16=self.use_fp16,
                    device=self.device,
                )
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[str] | list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Rerank chunks by cross-encoder relevance to query.

        Accepts raw strings or dicts with a "text" field. Returns the top_k items
        (same shape as input dict items, with an added "rerank_score") sorted desc.
        """
        if not chunks:
            return []
        is_dict = isinstance(chunks[0], dict)
        texts = [c["text"] if is_dict else c for c in chunks]
        model = self._ensure_model()
        pairs = [[query, t] for t in texts]
        scores = model.compute_score(pairs, normalize=True)
        if isinstance(scores, float):
            scores = [scores]

        items: list[dict[str, Any]] = []
        for i, score in enumerate(scores):
            item = dict(chunks[i]) if is_dict else {"text": texts[i]}
            item["rerank_score"] = float(score)
            items.append(item)
        items.sort(key=lambda x: x["rerank_score"], reverse=True)
        return items[:top_k]
