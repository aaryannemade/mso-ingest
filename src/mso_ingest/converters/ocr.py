"""Recover text from PDF pages that carry no text layer."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from ..tools import poppler, tesseract

# Rasterise well above screen resolution: tesseract's accuracy falls off
# sharply below roughly 300 dpi.
RENDER_DPI = 300


def pages_to_text(source: Path, pages: Sequence[int], *, lang: str) -> dict[int, str]:
    """OCR the given 1-based page numbers of ``source``.

    Pages that yield nothing are simply absent from the result. Raises
    :class:`~mso_ingest.tools.process.ToolError` if rendering or OCR fails.
    """
    recovered: dict[int, str] = {}

    with tempfile.TemporaryDirectory(prefix="mso-ocr-") as tmp:
        tmpdir = Path(tmp)
        for number in pages:
            images = poppler.to_pngs(
                source, tmpdir, prefix=f"p{number}", dpi=RENDER_DPI, first=number, last=number
            )
            if not images:
                continue

            text = tesseract.image_to_text(images[0], lang=lang)
            if text:
                recovered[number] = text
            images[0].unlink(missing_ok=True)

    return recovered
