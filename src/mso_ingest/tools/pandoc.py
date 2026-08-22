"""Pandoc."""

from __future__ import annotations

from pathlib import Path

from .process import require, run


def to_markdown(
    src: Path,
    dest: Path,
    *,
    from_fmt: str | None = None,
    media_dir: Path | None = None,
) -> None:
    """Convert ``src`` to GitHub-flavoured markdown at ``dest``.

    Unwrapped output keeps one source paragraph on one line, which reads
    better in a diff and avoids reflowing surprises downstream.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [require("pandoc")]
    if from_fmt:
        cmd += ["-f", from_fmt]
    cmd += ["-t", "gfm", "--wrap=none", "--markdown-headings=atx"]
    if media_dir is not None:
        cmd += [f"--extract-media={media_dir}"]
    cmd += ["-o", str(dest), str(src)]

    run(cmd)
