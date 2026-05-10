"""bge-m3 wrapper: dense (1024-d, L2-normalized) + sparse (lexical weights)."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BGEEmbedder:
    """Wrap BGE-M3 to return both dense and sparse representations."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        use_fp16: bool = True,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.resolved_device()
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self._model = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel

            logger.info("Loading embedder %s on %s (fp16=%s)", self.model_name, self.device, self.use_fp16)
            try:
                self._model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=self.use_fp16,
                    devices=self.device,
                )
            except TypeError:
                # Older FlagEmbedding uses `device` (singular).
                self._model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=self.use_fp16,
                    device=self.device,
                )
        return self._model

    @staticmethod
    def _l2_normalize(v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v)
        if norm < 1e-12:
            return v
        return v / norm

    def encode(self, text: str) -> dict[str, Any]:
        """Encode a single text. Returns {"dense": np.ndarray, "sparse": {int: float}}."""
        out = self.encode_batch([text])
        return {"dense": out["dense"][0], "sparse": out["sparse"][0]}

    def encode_batch(self, texts: list[str], batch_size: int = 8) -> dict[str, Any]:
        """Batch encode. Returns {"dense": np.ndarray[N,1024], "sparse": list[dict]}."""
        model = self._ensure_model()
        result = model.encode(
            texts,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = np.asarray(result["dense_vecs"], dtype=np.float32)
        # L2-normalize each row.
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms < 1e-12] = 1.0
        dense = dense / norms

        raw_sparse = result["lexical_weights"]
        sparse: list[dict[int, float]] = []
        for sw in raw_sparse:
            sparse.append({int(k): float(v) for k, v in sw.items()})

        return {"dense": dense, "sparse": sparse}
