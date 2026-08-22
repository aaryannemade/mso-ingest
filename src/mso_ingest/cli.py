"""Command line entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from . import converters, detect, manifest
from .converters.base import Context, sanitize, unique

app = typer.Typer(
    add_completion=False,
    help="Convert Microsoft Office documents into markdown, CSV and PNG for AI agents.",
)

console = Console(stderr=True)


def _collect(inputs: list[Path], recursive: bool) -> list[Path]:
    """Expand the given paths into a sorted, de-duplicated list of files."""
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in inputs:
        path = raw.expanduser()
        if path.is_dir():
            if not recursive:
                console.print(f"[yellow]skipping directory[/] {path} (use --recursive)")
                continue
            candidates = sorted(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in detect.SUPPORTED_EXTENSIONS
            )
        elif path.is_file():
            candidates = [path]
        else:
            console.print(f"[red]no such path[/] {path}")
            continue

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(candidate)

    return found


def _output_dir(source: Path, root: Path, taken: set[str]) -> Path:
    """Pick a per-document directory under ``root``.

    Every document gets its own directory even when it produces a single file,
    so the layout does not change shape depending on the input type.
    """
    name = unique(sanitize(source.stem, fallback="document"), taken)
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.command()
def main(
    inputs: Annotated[
        list[Path],
        typer.Argument(help="Files or directories to convert.", show_default=False),
    ],
    output: Annotated[Path, typer.Option("-o", "--output", help="Output root directory.")] = Path(
        "out"
    ),
    recursive: Annotated[
        bool,
        typer.Option("--recursive/--no-recursive", help="Descend into directories."),
    ] = True,
    dpi: Annotated[
        int, typer.Option("--dpi", min=36, max=600, help="Resolution for rendered slides.")
    ] = 150,
    ocr: Annotated[
        bool, typer.Option("--ocr/--no-ocr", help="OCR PDF pages that have no text layer.")
    ] = True,
    ocr_lang: Annotated[
        str, typer.Option("--ocr-lang", help="tesseract language code(s), e.g. 'eng+deu'.")
    ] = "eng",
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Only report problems.")] = False,
) -> None:
    """Convert each input document into its own directory under OUTPUT."""
    files = _collect(inputs, recursive)
    if not files:
        console.print("[red]nothing to convert[/]")
        raise typer.Exit(code=2)

    root = output.expanduser()
    root.mkdir(parents=True, exist_ok=True)

    documents: list[manifest.Document] = []
    taken: set[str] = set()

    for source in files:
        kind, detect_warning = detect.detect(source)
        outdir = _output_dir(source, root, taken)

        doc = manifest.Document(
            source=str(source),
            kind=kind,
            status=manifest.OK,
            output_dir=outdir.relative_to(root).as_posix(),
            source_bytes=source.stat().st_size,
            sha256=manifest.sha256_of(source),
        )
        if detect_warning:
            doc.warnings.append(detect_warning)

        if kind not in converters.SUPPORTED_KINDS:
            doc.status = manifest.ERROR
            doc.error = f"unsupported file type: {kind}"
            console.print(f"[red]skip[/] {source} ({doc.error})")
            documents.append(doc)
            continue

        try:
            result = converters.convert(
                kind,
                Context(
                    source=source,
                    outdir=outdir,
                    stem=sanitize(source.stem, fallback="document"),
                    dpi=dpi,
                    ocr=ocr,
                    ocr_lang=ocr_lang,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the batch
            doc.status = manifest.ERROR
            doc.error = f"{type(exc).__name__}: {exc}"
            console.print(f"[red]fail[/] {source}: {doc.error}")
            documents.append(doc)
            continue

        doc.artifacts = result.artifacts
        doc.warnings.extend(result.warnings)
        if not result.artifacts:
            doc.status = manifest.ERROR
            doc.error = "converter produced no output"
        elif result.degraded:
            doc.status = manifest.PARTIAL

        documents.append(doc)

        if not quiet:
            colour = {manifest.OK: "green", manifest.PARTIAL: "yellow", manifest.ERROR: "red"}[
                doc.status
            ]
            console.print(
                f"[{colour}]{doc.status}[/] {source} -> {doc.output_dir}/ "
                f"({len(doc.artifacts)} artifact{'s' if len(doc.artifacts) != 1 else ''})"
            )
        for warning in doc.warnings:
            console.print(f"  [yellow]warn[/] {warning}")

    manifest_path = manifest.write(root, documents)

    failed = sum(1 for d in documents if d.status == manifest.ERROR)
    if not quiet:
        console.print(f"\nmanifest: {manifest_path}")
    if failed:
        console.print(f"[red]{failed} of {len(documents)} document(s) failed[/]")
        raise typer.Exit(code=1)


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    sys.exit(app())
