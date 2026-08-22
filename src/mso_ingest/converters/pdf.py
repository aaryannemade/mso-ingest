"""``.pdf`` -> a single page-delimited markdown file, OCR'd where necessary."""

from __future__ import annotations

from pathlib import Path

from ..manifest import MARKDOWN
from ..tools import ToolError
from . import ocr, page_markdown
from .context import Context, Result

# Below this many non-whitespace characters a page is treated as image-only.
# Scanned pages usually extract to nothing at all; the margin covers a page
# carrying just a header or a page number in its text layer.
TEXT_YIELD_THRESHOLD = 24


def convert(ctx: Context) -> Result:
    result = Result()

    pages = _page_texts(ctx.source, result)
    if pages is None:
        return result

    imageonly = _pages_without_text(pages)
    recovered = _recover(ctx, imageonly, result)

    md_path = ctx.outdir / f"{ctx.stem}.md"
    md_path.write_text(page_markdown.build(pages, recovered), encoding="utf-8")
    result.add(
        md_path,
        MARKDOWN,
        root=ctx.root,
        meta={"pages": len(pages), "ocr_pages": sorted(recovered)},
    )
    return result


def _page_texts(source: Path, result: Result) -> list[str] | None:
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


def _pages_without_text(pages: list[str]) -> list[int]:
    return [n for n, text in enumerate(pages, start=1) if len(text.strip()) < TEXT_YIELD_THRESHOLD]


def _recover(ctx: Context, imageonly: list[int], result: Result) -> dict[int, str]:
    """OCR the pages that have no text layer, warning about whatever is left."""
    if not imageonly:
        return {}

    if not ctx.ocr:
        result.warn(
            f"{len(imageonly)} page(s) have no text layer and OCR is disabled: "
            f"{page_markdown.summarise(imageonly)}",
            degraded=True,
        )
        return {}

    try:
        recovered = ocr.pages_to_text(ctx.source, imageonly, lang=ctx.ocr_lang)
    except ToolError as exc:
        result.warn(f"OCR failed ({exc}); scanned pages left empty", degraded=True)
        recovered = {}

    still_empty = [n for n in imageonly if not recovered.get(n)]
    if still_empty:
        result.warn(
            f"{len(still_empty)} page(s) yielded no text even after OCR: "
            f"{page_markdown.summarise(still_empty)}",
            degraded=True,
        )
    return recovered
