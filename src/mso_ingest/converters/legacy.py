"""Upgrade legacy OLE2 documents to their modern equivalent.

Nothing else in the pipeline can read the old binary ``.doc``/``.ppt``
formats, so LibreOffice rewrites them first. The round trip is lossy enough
to be worth flagging on the document.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..kinds import LEGACY_TO_MODERN
from ..tools import ToolError, libreoffice
from .errors import UnsupportedDocument


@contextmanager
def upgraded(source: Path, kind: str) -> Iterator[Path]:
    """Yield a modern-format copy of ``source``, valid for the block's duration."""
    modern = LEGACY_TO_MODERN[kind]

    with tempfile.TemporaryDirectory(prefix="mso-legacy-") as tmp:
        try:
            converted = libreoffice.convert(source, modern, Path(tmp))
        except ToolError as exc:
            raise UnsupportedDocument(
                f"could not upgrade legacy {kind} via soffice: {exc}"
            ) from exc
        yield converted


def warning(kind: str) -> str:
    modern = LEGACY_TO_MODERN[kind]
    return (
        f"legacy .{kind} was converted to .{modern} by LibreOffice first; "
        "some formatting may differ from the original"
    )
