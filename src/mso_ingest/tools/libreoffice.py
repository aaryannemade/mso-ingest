"""LibreOffice, via the ``soffice`` CLI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .process import DEFAULT_TIMEOUT, ToolError, require, run


def convert(src: Path, target: str, outdir: Path, *, timeout: int = DEFAULT_TIMEOUT) -> Path:
    """Convert ``src`` to ``target`` (e.g. ``"pdf"``) inside ``outdir``.

    Each invocation gets a throwaway user profile. LibreOffice serialises on a
    lock in that profile, so sharing one makes concurrent conversions block or
    fail against each other.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mso-soffice-") as profile:
        run(
            [
                require("soffice"),
                "--headless",
                "--norestore",
                "--invisible",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to",
                target,
                "--outdir",
                str(outdir),
                str(src),
            ],
            timeout=timeout,
        )

    produced = outdir / f"{src.stem}.{target.split(':')[0]}"
    if not produced.exists():
        # soffice regularly exits 0 having converted nothing at all, so the
        # return code alone is not enough to tell whether this worked.
        raise ToolError(f"soffice produced no {target} output for {src.name}")
    return produced
