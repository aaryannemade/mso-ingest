"""Identify a file from its bytes, ignoring whatever the extension claims."""

from __future__ import annotations

import zipfile
from pathlib import Path

from . import kinds

# Returned when the file is a legacy OLE2 compound document. Which *kind* of
# legacy document it is cannot be told from the header alone -- .doc, .ppt and
# .xls share it -- so the caller resolves that using the extension.
OLE2 = "ole2"

_ZIP = b"PK\x03\x04"
_PDF = b"%PDF-"
_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Entries that identify each OOXML flavour inside the zip.
_OOXML_MARKERS = (
    ("word/document.xml", kinds.DOCX),
    ("ppt/presentation.xml", kinds.PPTX),
    ("xl/workbook.xml", kinds.XLSX),
)


def is_ole2(path: Path) -> bool:
    """True when ``path`` is a legacy OLE2 compound document."""
    return _header(path) == _OLE2


def sniff(path: Path) -> str | None:
    """Return a kind, :data:`OLE2`, or ``None`` if the bytes say nothing useful."""
    header = _header(path)
    if header.startswith(_PDF):
        return kinds.PDF
    if header == _OLE2:
        return OLE2
    if header.startswith(_ZIP):
        return _ooxml_flavour(path)
    return None


def _header(path: Path, size: int = 8) -> bytes:
    try:
        with path.open("rb") as fh:
            return fh.read(size)
    except OSError:
        return b""


def _ooxml_flavour(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError):
        return None
    for marker, kind in _OOXML_MARKERS:
        if marker in names:
            return kind
    return None
