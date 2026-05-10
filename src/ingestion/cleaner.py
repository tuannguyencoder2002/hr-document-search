"""Vietnamese-aware text cleaning: NFC normalize, strip control chars, collapse whitespace."""

from __future__ import annotations

import re
import unicodedata

# Match C0/C1 control characters except newline / tab.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Collapse runs of spaces/tabs (but keep newlines).
_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
# Collapse 3+ newlines -> 2.
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
# Trailing spaces at end of line.
_TRAILING_SPACES_RE = re.compile(r"[ \t]+\n")


def clean_text(text: str) -> str:
    """Normalize Vietnamese text and remove noise.

    Steps:
      1. Unicode NFC normalization (merge combining marks).
      2. Remove control characters.
      3. Collapse horizontal whitespace.
      4. Trim trailing whitespace on each line.
      5. Collapse 3+ blank lines to 2.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _TRAILING_SPACES_RE.sub("\n", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()
