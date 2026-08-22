"""``.pdf`` -> a single page-delimited markdown file, with OCR for scanned pages."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .. import external
from ..manifest import MARKDOWN
from .base import Context, Result

# Below this many non-whitespace characters a page is treated as image-only.
# Scanned pages usually extract to nothing at all; the margin covers pages
# carrying just a header or a page number in a text layer.
TEXT_YIELD_THRESHOLD = 24

# Rasterise for OCR well above screen resolution -- tesseract's accuracy falls
# off sharply below ~300 dpi.
OCR_DPI = 300


def convert(ctx: Context) -> Result:
    result = Result()
    pages = _extract_pages(ctx.source, result)

    if pages is None:
        return result

    empty = [n for n, text in enumerate(pages, start=1) if len(text.strip()) < TEXT_YIELD_THRESHOLD]
    ocr_pages: dict[int, str] = {}

    if empty and ctx.ocr:
        ocr_pages = _ocr(ctx, empty, result)

    if empty and not ctx.ocr:
        result.warn(
            f"{len(empty)} page(s) have no text layer and OCR is disabled: {_summarise(empty)}",
            degraded=True,
        )

    still_empty = [n for n in empty if not ocr_pages.get(n)]
    if still_empty and ctx.ocr:
        result.warn(
            f"{len(still_empty)} page(s) yielded no text even after OCR: {_summarise(still_empty)}",
            degraded=True,
        )

    md_path = ctx.outdir / f"{ctx.stem}.md"
    md_path.write_text(_render(pages, ocr_pages), encoding="utf-8")
    result.add(
        md_path,
        MARKDOWN,
        root=ctx.outdir.parent,
        meta={"pages": len(pages), "ocr_pages": sorted(ocr_pages)},
    )
    return result


def _extract_pages(source: Path, result: Result) -> list[str] | None:
    """Extract text per page in a single pass over the document."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer

    try:
        return [
            "".join(el.get_text() for el in layout if isinstance(el, LTTextContainer))
            for layout in extract_pages(str(source))
        ]
    except Exception as exc:  # noqa: BLE001 - pdfminer raises a wide range
        result.warn(f"pdf text extraction failed: {exc}", degraded=True)
        return None


def _ocr(ctx: Context, pages: list[int], result: Result) -> dict[int, str]:
    out: dict[int, str] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="mso-ocr-") as tmp:
            tmpdir = Path(tmp)
            for number in pages:
                images = external.pdf_to_pngs(
                    ctx.source,
                    tmpdir,
                    prefix=f"p{number}",
                    dpi=OCR_DPI,
                    first=number,
                    last=number,
                )
                if not images:
                    continue
                text = external.ocr_image(images[0], lang=ctx.ocr_lang)
                if text:
                    out[number] = text
                images[0].unlink(missing_ok=True)
    except external.ToolError as exc:
        result.warn(f"OCR failed ({exc}); scanned pages left empty", degraded=True)
    return out


def _render(pages: list[str], ocr_pages: dict[int, str]) -> str:
    chunks: list[str] = []
    for number, text in enumerate(pages, start=1):
        if number in ocr_pages:
            # Flagged so a reader knows this text is a transcription guess.
            chunks.append(f"<!-- Page {number} (OCR) -->\n\n{ocr_pages[number].strip()}")
        else:
            body = text.strip()
            marker = f"<!-- Page {number} -->"
            chunks.append(f"{marker}\n\n{body}" if body else marker)
    return "\n\n".join(chunks).rstrip() + "\n"


def _summarise(numbers: list[int], limit: int = 12) -> str:
    shown = ", ".join(str(n) for n in numbers[:limit])
    return shown if len(numbers) <= limit else f"{shown}, ... (+{len(numbers) - limit} more)"
