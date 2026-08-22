"""Dispatch a document to the converter for its kind."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .. import kinds
from . import docx, legacy, pdf, pptx, xlsx
from .context import Context, Result
from .errors import UnsupportedDocument

_CONVERTERS: dict[str, Callable[[Context], Result]] = {
    kinds.DOCX: docx.convert,
    kinds.PPTX: pptx.convert,
    kinds.XLSX: xlsx.convert,
    kinds.PDF: pdf.convert,
}

SUPPORTED_KINDS = frozenset(_CONVERTERS) | frozenset(kinds.LEGACY_TO_MODERN)

__all__ = ["SUPPORTED_KINDS", "Context", "Result", "UnsupportedDocument", "convert"]


def convert(kind: str, ctx: Context) -> Result:
    """Convert ``ctx.source``, transparently upgrading legacy binary formats."""
    if kind in kinds.LEGACY_TO_MODERN:
        return _convert_legacy(kind, ctx)

    handler = _CONVERTERS.get(kind)
    if handler is None:
        raise UnsupportedDocument(f"no converter for {kind!r}")
    return handler(ctx)


def _convert_legacy(kind: str, ctx: Context) -> Result:
    modern = kinds.LEGACY_TO_MODERN[kind]

    with legacy.upgraded(ctx.source, kind) as source:
        result = _CONVERTERS[modern](replace(ctx, source=source))

    result.warn(legacy.warning(kind), degraded=True)
    return result
