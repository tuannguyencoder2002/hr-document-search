"""Cross-encoder reranker using bge-reranker-v2-m3.

Uses sentence_transformers.CrossEncoder (fast tokenizer, stable API) instead of
FlagEmbedding.FlagReranker to avoid the `XLMRobertaTokenizer has no attribute
prepare_for_model` error triggered by newer transformers versions.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    # Numerically-stable sigmoid.
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


class CrossEncoderReranker:
    """Lazy-loaded cross-encoder reranker."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        use_fp16: bool = True,
        max_length: int = 512,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.reranker_model
        self.device = device or settings.resolved_device()
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self.max_length = max_length
        self._model = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            logger.info(
                "Loading reranker %s on %s (fp16=%s)",
                self.model_name,
                self.device,
                self.use_fp16,
            )
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=self.max_length,
            )
            if self.use_fp16:
                try:
                    self._model.model.half()
                except Exception as e:
                    logger.warning("fp16 conversion failed, falling back to fp32: %s", e)
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
        Scores are sigmoid-normalized to [0, 1] for display consistency.
        """
        if not chunks:
            return []
        is_dict = isinstance(chunks[0], dict)
        texts = [c["text"] if is_dict else c for c in chunks]
        model = self._ensure_model()
        pairs = [(query, t) for t in texts]
        raw_scores = model.predict(pairs, convert_to_numpy=True, show_progress_bar=False)
        scores = _sigmoid(np.asarray(raw_scores, dtype=np.float32))

        items: list[dict[str, Any]] = []
        for i, score in enumerate(scores):
            item = dict(chunks[i]) if is_dict else {"text": texts[i]}
            item["rerank_score"] = float(score)
            items.append(item)
        items.sort(key=lambda x: x["rerank_score"], reverse=True)
        return items[:top_k]
