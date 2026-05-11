"""HuggingFace Hub configuration.

We DO NOT force HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE by default because:
  1. CLIP (and any new model) needs a one-time download on first use.
  2. Those env vars are read at import time in huggingface_hub, so flipping
     them at runtime has no effect.

We only disable telemetry and implicit token discovery. Cached models will
still load without network because huggingface_hub checks the local cache
first — the "offline" flag is only needed when you want to FORBID all
network lookups even when the cache is present.

If you truly want full offline (airgap) mode, export HF_HUB_OFFLINE=1 in
your shell before launching the FastAPI server, after you've pre-downloaded
every model you need.
"""

from __future__ import annotations

import os


def enable_offline_by_default() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")


enable_offline_by_default()
