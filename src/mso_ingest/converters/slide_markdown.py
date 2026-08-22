"""Splice rendered slide images into a deck's extracted markdown.

Pure text manipulation: it takes markitdown's output and the list of rendered
images, and returns the combined markdown plus anything worth warning about.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

# markitdown emits this line before every slide's text. It is the anchor that
# lets the matching image be placed with the right slide.
SLIDE_MARKER = re.compile(r"^<!--\s*Slide number:\s*(\d+)\s*-->\s*$")


def build(text: str, images: Sequence[Path]) -> tuple[str, list[str]]:
    """Return ``(markdown, warnings)`` for a deck."""
    lines = text.splitlines()
    numbered = {number: image for number, image in enumerate(images, start=1)}
    warnings = _check_alignment(lines, images)

    if not _marker_numbers(lines):
        return _gallery(lines, images), warnings
    return _interleaved(lines, numbered), warnings


def _marker_numbers(lines: Sequence[str]) -> set[int]:
    return {int(m.group(1)) for line in lines if (m := SLIDE_MARKER.match(line))}


def _check_alignment(lines: Sequence[str], images: Sequence[Path]) -> list[str]:
    markers = _marker_numbers(lines)
    if images and markers and len(markers) != len(images):
        return [
            f"deck has {len(images)} rendered slides but markdown has {len(markers)} "
            "slide markers; images may be misaligned"
        ]
    return []


def _gallery(lines: Sequence[str], images: Sequence[Path]) -> str:
    """Fallback when there are no markers to anchor to: append the images."""
    out = list(lines)
    if images:
        out += ["", "## Slides", ""]
        out += [_link(n, p) for n, p in enumerate(images, start=1)]
    return _joined(out)


def _interleaved(lines: Sequence[str], numbered: dict[int, Path]) -> str:
    out: list[str] = []
    pending: int | None = None

    for line in lines:
        marker = SLIDE_MARKER.match(line)
        if marker:
            out.append(line)
            pending = int(marker.group(1))
            continue

        if pending is not None and line.strip():
            # Keep the slide's own heading first so it still introduces the
            # slide, with the image directly beneath it.
            if line.lstrip().startswith("#"):
                out.append(line)
                out.extend(_image_block(pending, numbered))
            else:
                out.extend(_image_block(pending, numbered))
                out.append(line)
            pending = None
            continue

        out.append(line)

    if pending is not None:
        out.extend(_image_block(pending, numbered))

    return _joined(out)


def _image_block(number: int, numbered: dict[int, Path]) -> list[str]:
    image = numbered.get(number)
    return ["", _link(number, image), ""] if image is not None else []


def _link(number: int, image: Path) -> str:
    return f"![Slide {number}](slides/{image.name})"


def _joined(lines: Sequence[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"
