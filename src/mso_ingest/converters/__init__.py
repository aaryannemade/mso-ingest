"""Dispatch a document to the converter for its kind."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from .. import detect, external
from . import docx, pdf, pptx, xlsx
from .base import Context, Result

_CONVERTERS: dict[str, Callable[[Context], Result]] = {
    detect.DOCX: docx.convert,
    detect.PPTX: pptx.convert,
    detect.XLSX: xlsx.convert,
    detect.PDF: pdf.convert,
}

SUPPORTED_KINDS = frozenset(_CONVERTERS) | frozenset(detect.LEGACY_TO_MODERN)


class UnsupportedDocument(RuntimeError):
    pass


def convert(kind: str, ctx: Context) -> Result:
    """Convert ``ctx.source``, transparently upgrading legacy binary formats."""
    modern = detect.LEGACY_TO_MODERN.get(kind)
    if modern is not None:
        return _convert_legacy(kind, modern, ctx)

    handler = _CONVERTERS.get(kind)
    if handler is None:
        raise UnsupportedDocument(f"no converter for {kind!r}")
    return handler(ctx)


def _convert_legacy(kind: str, modern: str, ctx: Context) -> Result:
    """Round legacy ``.doc``/``.ppt`` through LibreOffice into the modern format.

    Nothing else in the pipeline can read the old OLE2 formats, and the
    round-trip is lossy enough to be worth flagging in the manifest.
    """
    with tempfile.TemporaryDirectory(prefix="mso-legacy-") as tmp:
        try:
            upgraded = external.soffice_convert(ctx.source, modern, Path(tmp))
        except external.ToolError as exc:
            raise UnsupportedDocument(
                f"could not upgrade legacy {kind} via soffice: {exc}"
            ) from exc

        result = convert(modern, Context(**{**ctx.__dict__, "source": upgraded}))

    result.warn(
        f"legacy .{kind} was converted to .{modern} by LibreOffice first; "
        "some formatting may differ from the original",
        degraded=True,
    )
    return result
