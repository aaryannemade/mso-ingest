"""Poppler's PDF utilities."""

from __future__ import annotations

from pathlib import Path

from .process import require, run


def to_pngs(
    pdf: Path,
    outdir: Path,
    *,
    prefix: str = "page",
    dpi: int = 150,
    first: int | None = None,
    last: int | None = None,
) -> list[Path]:
    """Rasterise ``pdf`` to PNGs named ``<prefix>-<n>.png``, in page order.

    pdftoppm zero-pads the page number to a fixed width per run, so sorting
    the results lexicographically already yields page order.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [require("pdftoppm"), "-png", "-r", str(dpi)]
    if first is not None:
        cmd += ["-f", str(first)]
    if last is not None:
        cmd += ["-l", str(last)]
    cmd += [str(pdf), str(outdir / prefix)]

    run(cmd)
    return sorted(outdir.glob(f"{prefix}-*.png"))
