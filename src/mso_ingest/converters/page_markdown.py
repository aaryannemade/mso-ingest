"""Assemble page-delimited markdown for a PDF."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

_SUMMARY_LIMIT = 12


def build(pages: Sequence[str], ocr_pages: Mapping[int, str]) -> str:
    """Render one markdown document from per-page text.

    Pages recovered by OCR are marked as such, so a reader can tell
    transcribed text from text that came out of the PDF's own text layer.
    """
    chunks: list[str] = []

    for number, extracted in enumerate(pages, start=1):
        transcribed = ocr_pages.get(number)
        if transcribed:
            chunks.append(f"<!-- Page {number} (OCR) -->\n\n{transcribed.strip()}")
            continue

        marker = f"<!-- Page {number} -->"
        body = extracted.strip()
        chunks.append(f"{marker}\n\n{body}" if body else marker)

    return "\n\n".join(chunks).rstrip() + "\n"


def summarise(numbers: Sequence[int], limit: int = _SUMMARY_LIMIT) -> str:
    """Render a page-number list for a warning, truncating a long tail."""
    shown = ", ".join(str(n) for n in numbers[:limit])
    if len(numbers) <= limit:
        return shown
    return f"{shown}, ... (+{len(numbers) - limit} more)"
