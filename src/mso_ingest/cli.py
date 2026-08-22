"""Command line entry point: option wiring only, the work lives elsewhere."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import discovery, manifest, pipeline
from .reporting import Reporter

app = typer.Typer(
    add_completion=False,
    help="Convert Microsoft Office documents into markdown, CSV and PNG for AI agents.",
)


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
    reporter = Reporter(quiet=quiet)

    found = discovery.collect(inputs, recursive=recursive)
    reporter.discovery(found)
    if not found.files:
        reporter.nothing_to_convert()
        raise typer.Exit(code=2)

    root = output.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    options = pipeline.Options(dpi=dpi, ocr=ocr, ocr_lang=ocr_lang)

    documents = []
    for outcome in pipeline.convert_all(found.files, root=root, options=options):
        reporter.outcome(outcome)
        documents.append(outcome.document)

    reporter.manifest_written(manifest.write(root, documents))

    failed = sum(1 for document in documents if document.status == manifest.ERROR)
    if failed:
        reporter.failures(failed, len(documents))
        raise typer.Exit(code=1)


def entrypoint() -> None:
    app()


if __name__ == "__main__":
    entrypoint()
