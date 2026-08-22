"""Convert a batch of documents, producing one manifest entry for each."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from . import converters, detect, manifest
from .converters import Context
from .paths import sanitize, unique

# How far a document got, which decides how it is reported.
UNSUPPORTED = "unsupported"  # nothing could read it; never attempted
CRASHED = "crashed"  # a converter raised
CONVERTED = "converted"  # a converter ran and produced a verdict


@dataclass(frozen=True)
class Options:
    """Conversion settings shared by every document in a run."""

    dpi: int = 150
    ocr: bool = True
    ocr_lang: str = "eng"


@dataclass(frozen=True)
class Outcome:
    document: manifest.Document
    stage: str


def convert_all(files: Iterable[Path], *, root: Path, options: Options) -> Iterator[Outcome]:
    """Convert each file, yielding results as they complete.

    Yielding lets the caller report progress on a long batch. One failure
    never stops the run: it becomes an ``error`` entry in the manifest.
    """
    taken: set[str] = set()
    for source in files:
        yield _convert_one(source, root=root, options=options, taken=taken)


def _convert_one(source: Path, *, root: Path, options: Options, taken: set[str]) -> Outcome:
    kind, warning = detect.detect(source)
    outdir = _output_dir(source, root, taken)
    document = _new_document(source, kind, outdir, root)

    if warning:
        document.warnings.append(warning)

    if kind not in converters.SUPPORTED_KINDS:
        document.status = manifest.ERROR
        document.error = f"unsupported file type: {kind}"
        return Outcome(document, UNSUPPORTED)

    try:
        result = converters.convert(kind, _context(source, outdir, options))
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the batch
        document.status = manifest.ERROR
        document.error = f"{type(exc).__name__}: {exc}"
        return Outcome(document, CRASHED)

    document.artifacts = result.artifacts
    document.warnings.extend(result.warnings)
    document.status = _status(result)
    if document.status == manifest.ERROR:
        document.error = "converter produced no output"

    return Outcome(document, CONVERTED)


def _status(result: converters.Result) -> str:
    if not result.artifacts:
        return manifest.ERROR
    return manifest.PARTIAL if result.degraded else manifest.OK


def _new_document(source: Path, kind: str, outdir: Path, root: Path) -> manifest.Document:
    return manifest.Document(
        source=str(source),
        kind=kind,
        status=manifest.OK,
        output_dir=outdir.relative_to(root).as_posix(),
        source_bytes=source.stat().st_size,
        sha256=manifest.sha256_of(source),
    )


def _context(source: Path, outdir: Path, options: Options) -> Context:
    return Context(
        source=source,
        outdir=outdir,
        stem=sanitize(source.stem, fallback="document"),
        dpi=options.dpi,
        ocr=options.ocr,
        ocr_lang=options.ocr_lang,
    )


def _output_dir(source: Path, root: Path, taken: set[str]) -> Path:
    """Give the document its own directory under ``root``.

    Every document gets one even when it produces a single file, so the layout
    does not change shape depending on the input type.
    """
    name = unique(sanitize(source.stem, fallback="document"), taken)
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path
