"""``.docx`` -> a single markdown file, plus any embedded media."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..manifest import MARKDOWN, MEDIA
from ..tools import ToolError, pandoc
from .context import Context, Result


def convert(ctx: Context) -> Result:
    result = Result()
    md_path = ctx.outdir / f"{ctx.stem}.md"
    media_dir = ctx.outdir / "media"

    # pandoc first: it understands docx styles, tables, footnotes and lists far
    # better than the generic extractors, and pulls out embedded images.
    try:
        pandoc.to_markdown(ctx.source, md_path, from_fmt="docx", media_dir=media_dir)
    except ToolError as exc:
        result.warn(f"pandoc failed ({exc}); fell back to markitdown", degraded=True)
        shutil.rmtree(media_dir, ignore_errors=True)
        _markitdown(ctx.source, md_path)

    result.add(md_path, MARKDOWN, root=ctx.root)
    _record_media(media_dir, result, root=ctx.root)
    return result


def _markitdown(source: Path, md_path: Path) -> None:
    from markitdown import MarkItDown

    md_path.write_text(MarkItDown().convert(str(source)).text_content, encoding="utf-8")


def _record_media(media_dir: Path, result: Result, *, root: Path) -> None:
    """Register extracted images, removing the directory if pandoc found none."""
    if not media_dir.exists():
        return

    images = sorted(p for p in media_dir.rglob("*") if p.is_file())
    for image in images:
        result.add(image, MEDIA, root=root)
    if not images:
        shutil.rmtree(media_dir)
