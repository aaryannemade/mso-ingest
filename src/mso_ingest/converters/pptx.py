"""``.pptx`` -> one markdown file with each slide's rendered PNG linked inline."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .. import external
from ..manifest import IMAGE, MARKDOWN
from .base import Context, Result, reset_dir

# markitdown emits this before every slide's text, which is what lets us splice
# the rendered images back in at the right positions.
_SLIDE_MARKER = re.compile(r"^<!--\s*Slide number:\s*(\d+)\s*-->\s*$")


def convert(ctx: Context) -> Result:
    result = Result()

    text = _extract_text(ctx.source)
    slides_dir = reset_dir(ctx.outdir / "slides")
    images = _render_slides(ctx, slides_dir, result)

    markdown = _interleave(text, images, result)
    md_path = ctx.outdir / f"{ctx.stem}.md"
    md_path.write_text(markdown, encoding="utf-8")

    root = ctx.outdir.parent
    result.add(md_path, MARKDOWN, root=root)
    for number, image in enumerate(images, start=1):
        result.add(image, IMAGE, root=root, meta={"slide": number})

    if not images:
        slides_dir.rmdir()

    return result


def _extract_text(source: Path) -> str:
    from markitdown import MarkItDown

    return MarkItDown().convert(str(source)).text_content


def _render_slides(ctx: Context, slides_dir: Path, result: Result) -> list[Path]:
    """Render every slide to a PNG via PDF.

    ``soffice --convert-to png`` only ever emits the first slide, so the PDF
    export is the intermediate that gets us the full deck.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="mso-pptx-") as tmp:
            pdf = external.soffice_convert(ctx.source, "pdf", Path(tmp))
            rendered = external.pdf_to_pngs(pdf, slides_dir, prefix="raw", dpi=ctx.dpi)
    except external.ToolError as exc:
        result.warn(f"slide rendering failed ({exc}); markdown has text only", degraded=True)
        return []

    width = max(2, len(str(len(rendered))))
    final: list[Path] = []
    for number, raw in enumerate(rendered, start=1):
        target = slides_dir / f"slide-{number:0{width}d}.png"
        raw.rename(target)
        final.append(target)
    return final


def _interleave(text: str, images: list[Path], result: Result) -> str:
    lines = text.splitlines()

    found = {int(m.group(1)) for line in lines if (m := _SLIDE_MARKER.match(line))}
    if images and found and len(found) != len(images):
        result.warn(
            f"deck has {len(images)} rendered slides but markdown has {len(found)} "
            "slide markers; images may be misaligned",
            degraded=True,
        )

    if not found:
        # No markers to anchor to: keep the text as-is and append a gallery.
        out = list(lines)
        if images:
            out += ["", "## Slides", ""]
            out += [f"![Slide {n}](slides/{p.name})" for n, p in enumerate(images, start=1)]
        return "\n".join(out).rstrip() + "\n"

    by_number = {n: p for n, p in enumerate(images, start=1)}
    out: list[str] = []
    pending: int | None = None

    for line in lines:
        match = _SLIDE_MARKER.match(line)
        if match:
            out.append(line)
            pending = int(match.group(1))
            continue

        # Place the image just after the slide's title so the heading still
        # introduces the slide, with the visual immediately beneath it.
        if pending is not None and line.strip():
            if line.lstrip().startswith("#"):
                out.append(line)
                out.extend(_image_block(pending, by_number))
            else:
                out.extend(_image_block(pending, by_number))
                out.append(line)
            pending = None
            continue

        out.append(line)

    if pending is not None:
        out.extend(_image_block(pending, by_number))

    return "\n".join(out).rstrip() + "\n"


def _image_block(number: int, by_number: dict[int, Path]) -> list[str]:
    image = by_number.get(number)
    if image is None:
        return []
    return ["", f"![Slide {number}](slides/{image.name})", ""]
