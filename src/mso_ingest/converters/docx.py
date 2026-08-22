"""``.docx`` -> a single markdown file (plus any embedded media)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .. import external
from ..manifest import MARKDOWN, MEDIA
from .base import Context, Result


def convert(ctx: Context) -> Result:
    result = Result()
    md_path = ctx.outdir / f"{ctx.stem}.md"
    media_dir = ctx.outdir / "media"

    # pandoc first: it understands docx styles, tables, footnotes and lists far
    # better than the generic extractors, and can pull out embedded images.
    try:
        external.pandoc_to_markdown(ctx.source, md_path, from_fmt="docx", media_dir=media_dir)
    except external.ToolError as exc:
        result.warn(f"pandoc failed ({exc}); fell back to markitdown", degraded=True)
        if media_dir.exists():
            shutil.rmtree(media_dir)
        _markitdown_fallback(ctx.source, md_path)

    result.add(md_path, MARKDOWN, root=ctx.outdir.parent)

    if media_dir.exists():
        images = sorted(p for p in media_dir.rglob("*") if p.is_file())
        for image in images:
            result.add(image, MEDIA, root=ctx.outdir.parent)
        if not images:
            shutil.rmtree(media_dir)

    return result


def _markitdown_fallback(source: Path, md_path: Path) -> None:
    from markitdown import MarkItDown

    text = MarkItDown().convert(str(source)).text_content
    md_path.write_text(text, encoding="utf-8")
