"""Thin wrappers around the external CLI tools the converters shell out to.

Every wrapper raises :class:`ToolError` on failure so callers can decide
between falling back to another engine and recording a warning.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 900


class ToolError(RuntimeError):
    """An external tool is missing, timed out, or exited non-zero."""


def find(name: str) -> str | None:
    """Return the absolute path to ``name``, or ``None`` if it is not installed."""
    return shutil.which(name)


def require(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise ToolError(f"required tool {name!r} was not found on PATH")
    return path


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    stdout_path: Path | None = None,
) -> str:
    """Run ``cmd``, returning stdout as text (empty when redirected to a file)."""
    require(cmd[0])

    sink = stdout_path.open("wb") if stdout_path is not None else None
    try:
        proc = subprocess.run(  # noqa: S603 - argv is built from literals + paths
            cmd,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            stdout=sink if sink is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{cmd[0]} timed out after {timeout}s") from exc
    finally:
        if sink is not None:
            sink.close()

    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise ToolError(f"{cmd[0]} exited {proc.returncode}: {detail[:800]}")

    return (proc.stdout or b"").decode("utf-8", "replace") if sink is None else ""


# --------------------------------------------------------------------------
# LibreOffice


def soffice_convert(
    src: Path, target: str, outdir: Path, *, timeout: int = DEFAULT_TIMEOUT
) -> Path:
    """Convert ``src`` to ``target`` (e.g. ``"pdf"``) inside ``outdir``.

    LibreOffice serialises on its user profile, so each invocation gets a
    throwaway profile. Without this, concurrent conversions silently block or
    fail against a shared lock.
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
        # soffice frequently exits 0 even when it converted nothing.
        raise ToolError(f"soffice produced no {target} output for {src.name}")
    return produced


# --------------------------------------------------------------------------
# poppler


def pdf_page_count(pdf: Path) -> int:
    out = run([require("pdfinfo"), str(pdf)])
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise ToolError(f"pdfinfo reported no page count for {pdf.name}")


def pdf_to_pngs(
    pdf: Path,
    outdir: Path,
    *,
    prefix: str = "page",
    dpi: int = 150,
    first: int | None = None,
    last: int | None = None,
) -> list[Path]:
    """Rasterise ``pdf`` to PNGs named ``<prefix>-<n>.png``.

    pdftoppm zero-pads the page number to a fixed width per run, so a plain
    lexicographic sort of the results is already in page order.
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


# --------------------------------------------------------------------------
# tesseract


def ocr_image(image: Path, *, lang: str = "eng", timeout: int = 300) -> str:
    return run([require("tesseract"), str(image), "stdout", "-l", lang], timeout=timeout).strip()


# --------------------------------------------------------------------------
# csvkit


def in2csv_sheet(src: Path, sheet: str, dest: Path, *, fmt: str | None = None) -> None:
    """Extract a single worksheet to ``dest`` as CSV.

    Two csvkit behaviours are worked around here:

    * ``--write-sheets`` writes its output next to the *input* file, which
      would scribble into the user's source tree; we redirect stdout instead.
    * csvkit's type inference is lossy -- a column holding only 0/1 is coerced
      to booleans, turning ``1`` into ``True``. ``-I`` disables it so cells
      survive verbatim.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [require("in2csv"), "-I", "--sheet", sheet]
    if fmt:
        cmd += ["-f", fmt]
    cmd += [str(src)]
    run(cmd, stdout_path=dest)


# --------------------------------------------------------------------------
# pandoc


def pandoc_to_markdown(
    src: Path,
    dest: Path,
    *,
    from_fmt: str | None = None,
    media_dir: Path | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [require("pandoc")]
    if from_fmt:
        cmd += ["-f", from_fmt]
    cmd += ["-t", "gfm", "--wrap=none", "--markdown-headings=atx"]
    if media_dir is not None:
        cmd += [f"--extract-media={media_dir}"]
    cmd += ["-o", str(dest), str(src)]
    run(cmd)
