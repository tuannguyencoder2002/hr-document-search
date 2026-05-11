"""Force HuggingFace / Transformers into full offline mode.

All models must already be cached locally. No network calls to huggingface.co.
If a model is missing from cache, it will error out — download it manually
first with: `huggingface-cli download <model_name>`
"""

from __future__ import annotations

import os


def enable_offline_by_default() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")


enable_offline_by_default()
