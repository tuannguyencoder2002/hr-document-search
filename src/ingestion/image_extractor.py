"""Extract embedded images from PDF / DOCX files.

Each extracted image is saved to disk with stable naming:
    <image_store_dir>/<source_stem>__p{page}_i{idx}.png

Returns a list of `ExtractedImage` records including metadata needed to
locate the image in the original document (source path + page number + bbox)
and a nearby caption/paragraph for cross-modal search.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedImage:
    """One image extracted from a document."""

    image_path: Path
    width: int
    height: int
    metadata: dict[str, Any] = field(default_factory=dict)


_MIN_PX_FALLBACK = 80


def _safe_stem(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name).strip("_") or "doc"


def _passes_size_filter(width: int, height: int) -> bool:
    settings = get_settings()
    min_w = getattr(settings, "image_min_width", _MIN_PX_FALLBACK)
    min_h = getattr(settings, "image_min_height", _MIN_PX_FALLBACK)
    return width >= min_w and height >= min_h


def extract_pdf_images(
    pdf_path: str | Path,
    out_dir: str | Path | None = None,
) -> list[ExtractedImage]:
    """Extract images from a PDF, one PNG per embedded image.

    Also captures page-level caption candidates (the raw page text) so a
    downstream encoder can use them as weak labels.
    """
    import fitz  # PyMuPDF
    from PIL import Image

    settings = get_settings()
    pdf_path = Path(pdf_path)
    out_base = Path(out_dir) if out_dir else Path(settings.image_store_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(pdf_path.stem)

    results: list[ExtractedImage] = []
    try:
        with fitz.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf, start=1):
                # Cache page text once for captions.
                page_text = (page.get_text("text") or "").strip()
                page_preview = page_text[:400]

                for fig_idx, img in enumerate(page.get_images(full=True), start=1):
                    xref = img[0]
                    try:
                        base = pdf.extract_image(xref)
                    except Exception as e:
                        logger.debug("extract_image failed for xref=%s: %s", xref, e)
                        continue
                    image_bytes = base.get("image")
                    if not image_bytes:
                        continue
                    try:
                        with Image.open(__import__("io").BytesIO(image_bytes)) as im:
                            im = im.convert("RGB")
                            w, h = im.size
                            if not _passes_size_filter(w, h):
                                continue
                            out_path = out_base / f"{stem}__p{page_index}_i{fig_idx}.png"
                            im.save(out_path, format="PNG", optimize=True)
                    except Exception as e:
                        logger.debug("PIL decode failed p=%s i=%s: %s", page_index, fig_idx, e)
                        continue

                    results.append(
                        ExtractedImage(
                            image_path=out_path,
                            width=w,
                            height=h,
                            metadata={
                                "source": pdf_path.name,
                                "source_path": str(pdf_path),
                                "page": page_index,
                                "figure_index": fig_idx,
                                "caption": page_preview,
                                "file_type": "pdf",
                            },
                        )
                    )
    except Exception as e:
        logger.warning("PDF image extraction failed for %s: %s", pdf_path, e)
    return results


def extract_docx_images(
    docx_path: str | Path,
    out_dir: str | Path | None = None,
) -> list[ExtractedImage]:
    """Extract images from a DOCX file via its relationships."""
    from docx import Document
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from PIL import Image

    settings = get_settings()
    docx_path = Path(docx_path)
    out_base = Path(out_dir) if out_dir else Path(settings.image_store_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(docx_path.stem)

    doc = Document(str(docx_path))
    caption_hint = " ".join(p.text for p in doc.paragraphs if p.text.strip())[:400]

    results: list[ExtractedImage] = []
    idx = 0
    for rel in doc.part.rels.values():
        if rel.reltype != RT.IMAGE:
            continue
        idx += 1
        try:
            image_bytes = rel.target_part.blob
            with Image.open(__import__("io").BytesIO(image_bytes)) as im:
                im = im.convert("RGB")
                w, h = im.size
                if not _passes_size_filter(w, h):
                    continue
                out_path = out_base / f"{stem}__p1_i{idx}.png"
                im.save(out_path, format="PNG", optimize=True)
        except Exception as e:
            logger.debug("DOCX image extract failed idx=%s: %s", idx, e)
            continue

        results.append(
            ExtractedImage(
                image_path=out_path,
                width=w,
                height=h,
                metadata={
                    "source": docx_path.name,
                    "source_path": str(docx_path),
                    "page": 1,
                    "figure_index": idx,
                    "caption": caption_hint,
                    "file_type": "docx",
                },
            )
        )
    return results


def extract_images(path: str | Path, out_dir: str | Path | None = None) -> list[ExtractedImage]:
    """Dispatch to PDF or DOCX extractor; returns [] for unsupported types."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_images(p, out_dir=out_dir)
    if ext == ".docx":
        return extract_docx_images(p, out_dir=out_dir)
    return []
