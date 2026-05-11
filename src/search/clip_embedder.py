"""CLIP wrapper: multilingual text encoder + image encoder, shared 512-d space.

- Text  : sentence-transformers/clip-ViT-B-32-multilingual-v1 (supports Vietnamese)
- Image : sentence-transformers/clip-ViT-B-32 (same embedding space)

Both models are lazy-loaded in fp16 on CUDA by default to keep VRAM low.
Vectors are L2-normalized so cosine similarity equals dot product in Qdrant.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any

import numpy as np

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@contextlib.contextmanager
def _allow_hf_download():
    """Temporarily disable HF offline mode so a missing model can be fetched once.

    The project defaults to HF_HUB_OFFLINE=1 / TRANSFORMERS_OFFLINE=1 to avoid
    unwanted Hub traffic on every boot. CLIP models are loaded on-demand and
    typically aren't in the cache yet — this context manager relaxes those
    env vars just for the current load, then restores them.
    """
    keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    saved = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ[k] = "0"
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class CLIPEmbedder:
    """Lazy-loaded CLIP text + image encoders."""

    def __init__(
        self,
        text_model: str | None = None,
        image_model: str | None = None,
        device: str | None = None,
        use_fp16: bool = True,
    ) -> None:
        settings = get_settings()
        self.text_model_name = text_model or settings.clip_text_model
        self.image_model_name = image_model or settings.clip_image_model
        self.device = device or settings.resolved_device()
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self._text_model = None
        self._image_model = None

    def _load_st(self, name: str) -> Any:
        """Load a SentenceTransformer. Tries cache first, falls back to HF download.

        HF_HUB_OFFLINE is a startup-time env var baked into huggingface_hub on
        import, so toggling os.environ at runtime has no effect. Instead we
        pass local_files_only=True first, and on failure we re-import with
        an explicit download attempt via huggingface_hub directly.
        """
        from sentence_transformers import SentenceTransformer

        # Try with local cache first.
        try:
            return SentenceTransformer(name, device=self.device, local_files_only=True)
        except Exception as e:
            logger.info("CLIP %s not in cache (%s) — downloading now…", name, type(e).__name__)

        # Force download via huggingface_hub's snapshot_download with
        # local_files_only explicitly False, bypassing the offline env flag.
        try:
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=name,
                local_files_only=False,  # explicit override of HF_HUB_OFFLINE
                etag_timeout=30,
            )
            return SentenceTransformer(name, device=self.device, local_files_only=True)
        except Exception as e:
            logger.error("CLIP download failed for %s: %s", name, e)
            raise

    def _ensure_text(self) -> Any:
        if self._text_model is None:
            logger.info(
                "Loading CLIP text model %s on %s (fp16=%s)",
                self.text_model_name,
                self.device,
                self.use_fp16,
            )
            self._text_model = self._load_st(self.text_model_name)
            if self.use_fp16:
                try:
                    self._text_model = self._text_model.half()
                except Exception as e:
                    logger.warning("CLIP text fp16 conversion failed: %s", e)
        return self._text_model

    def _ensure_image(self) -> Any:
        if self._image_model is None:
            logger.info(
                "Loading CLIP image model %s on %s (fp16=%s)",
                self.image_model_name,
                self.device,
                self.use_fp16,
            )
            self._image_model = self._load_st(self.image_model_name)
            if self.use_fp16:
                try:
                    self._image_model = self._image_model.half()
                except Exception as e:
                    logger.warning("CLIP image fp16 conversion failed: %s", e)
        return self._image_model

    @staticmethod
    def _l2_normalize_rows(x: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(x, axis=1, keepdims=True)
        norms[norms < 1e-12] = 1.0
        return x / norms

    def encode_text(self, texts: str | list[str], batch_size: int = 16) -> np.ndarray:
        """Encode text(s). Returns (N, 512) float32, L2-normalized."""
        if isinstance(texts, str):
            texts = [texts]
        model = self._ensure_text()
        emb = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return self._l2_normalize_rows(np.asarray(emb, dtype=np.float32))

    def encode_image(
        self,
        images: "str | Path | list[str | Path] | Any",
        batch_size: int = 8,
    ) -> np.ndarray:
        """Encode image path(s) or PIL Image(s). Returns (N, 512) float32, L2-normalized."""
        from PIL import Image

        if not isinstance(images, list):
            images = [images]
        pil_imgs = []
        for img in images:
            if isinstance(img, (str, Path)):
                pil_imgs.append(Image.open(img).convert("RGB"))
            else:
                pil_imgs.append(img.convert("RGB") if img.mode != "RGB" else img)

        model = self._ensure_image()
        emb = model.encode(
            pil_imgs,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return self._l2_normalize_rows(np.asarray(emb, dtype=np.float32))

    def unload(self) -> None:
        """Free CLIP weights from memory. Useful under VRAM pressure."""
        self._text_model = None
        self._image_model = None
        try:
            import torch

            if self.device == "cuda":
                torch.cuda.empty_cache()
        except ImportError:
            pass
