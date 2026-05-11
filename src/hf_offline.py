"""Force HuggingFace / Transformers into offline mode.

Must be imported **before** any transformers / sentence_transformers /
huggingface_hub / FlagEmbedding import. See entry-point scripts for usage.

Users can override by setting HF_HUB_OFFLINE=0 in the shell before launch,
e.g. to download a new model once, then switch back to offline.
"""

from __future__ import annotations

import os


def enable_offline_by_default() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")


enable_offline_by_default()
