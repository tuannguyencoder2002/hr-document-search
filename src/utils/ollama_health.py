"""Ollama health / diagnostics helpers.

Use `log_model_status()` to print whether the configured model is loaded,
how much of it is on GPU, and the keep-alive timer. Handy for diagnosing
"my generate takes 60s" (usually means model is CPU-only or not resident).
"""

from __future__ import annotations

from typing import Any

import requests

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_running_models(url: str | None = None, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Call Ollama's /api/ps endpoint. Returns list of currently loaded models."""
    settings = get_settings()
    base = url or settings.ollama_url
    try:
        r = requests.get(f"{base}/api/ps", timeout=timeout)
        r.raise_for_status()
        return (r.json() or {}).get("models", [])
    except Exception as e:
        logger.warning("Could not query Ollama /api/ps: %s", e)
        return []


def log_model_status(model_name: str | None = None) -> dict[str, Any] | None:
    """Log whether `model_name` is resident and how much is on GPU.

    Returns the raw entry for the model (or None if not loaded).
    """
    settings = get_settings()
    target = model_name or settings.ollama_model
    models = get_running_models()
    if not models:
        logger.warning(
            "Ollama has no models resident (expected '%s'). First request will be "
            "slow because the model has to load from disk.",
            target,
        )
        return None

    for m in models:
        name = m.get("name") or m.get("model") or ""
        if name.startswith(target) or target.startswith(name):
            size = int(m.get("size") or 0)
            size_vram = int(m.get("size_vram") or 0)
            pct = (100.0 * size_vram / size) if size else 0.0
            expires = m.get("expires_at", "?")
            logger.info(
                "Ollama model resident: %s | total=%.2fGB, on_gpu=%.2fGB (%.0f%%) | expires=%s",
                name, size / 1e9, size_vram / 1e9, pct, expires,
            )
            if size and size_vram < size * 0.95:
                logger.warning(
                    "Model is NOT fully on GPU — generate will be slow. "
                    "Consider OLLAMA_NUM_GPU=-1 or reducing context length."
                )
            return m

    logger.warning(
        "Model '%s' not resident. Currently loaded: %s",
        target,
        [m.get("name") for m in models],
    )
    return None
