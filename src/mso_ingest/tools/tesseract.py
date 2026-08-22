"""Tesseract OCR."""

from __future__ import annotations

from pathlib import Path

from .process import require, run


def image_to_text(image: Path, *, lang: str = "eng", timeout: int = 300) -> str:
    """Read text out of ``image``. ``lang`` may combine codes, e.g. ``eng+deu``."""
    return run([require("tesseract"), str(image), "stdout", "-l", lang], timeout=timeout).strip()
