"""``.pptx`` -> one markdown file with each slide's rendered PNG linked inline."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..manifest import IMAGE, MARKDOWN
from ..paths import reset_dir
from ..tools import ToolError, libreoffice, poppler
from . import slide_markdown
from .context import Context, Result


def convert(ctx: Context) -> Result:
    result = Result()

    slides_dir = reset_dir(ctx.outdir / "slides")
    images = _render_slides(ctx, slides_dir, result)

    markdown, warnings = slide_markdown.build(_extract_text(ctx.source), images)
    for warning in warnings:
        result.warn(warning, degraded=True)

    md_path = ctx.outdir / f"{ctx.stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    result.add(md_path, MARKDOWN, root=ctx.root)
    for number, image in enumerate(images, start=1):
        result.add(image, IMAGE, root=ctx.root, meta={"slide": number})

    if not images:
        slides_dir.rmdir()

    return result


def _extract_text(source: Path) -> str:
    from markitdown import MarkItDown

    return MarkItDown().convert(str(source)).text_content


def _render_slides(ctx: Context, slides_dir: Path, result: Result) -> list[Path]:
    """Render every slide to a PNG, going via PDF.

    ``soffice --convert-to png`` only ever emits the first slide of a deck, so
    the PDF export is the intermediate that gets us all of them.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="mso-pptx-") as tmp:
            pdf = libreoffice.convert(ctx.source, "pdf", Path(tmp))
            rendered = poppler.to_pngs(pdf, slides_dir, prefix="raw", dpi=ctx.dpi)
    except ToolError as exc:
        result.warn(f"slide rendering failed ({exc}); markdown has text only", degraded=True)
        return []

    return _number_slides(rendered, slides_dir)


def _number_slides(rendered: list[Path], slides_dir: Path) -> list[Path]:
    """Rename pdftoppm's output to a stable, zero-padded ``slide-NN.png``."""
    width = max(2, len(str(len(rendered))))
    final: list[Path] = []
    for number, raw in enumerate(rendered, start=1):
        target = slides_dir / f"slide-{number:0{width}d}.png"
        raw.rename(target)
        final.append(target)
    return final
