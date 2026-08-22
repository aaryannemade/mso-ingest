"""Work out what kind of document a file actually is."""

from __future__ import annotations

import zipfile
from pathlib import Path

# Canonical kinds the converters dispatch on.
DOCX = "docx"
PPTX = "pptx"
XLSX = "xlsx"
PDF = "pdf"
UNKNOWN = "unknown"

# Legacy binary formats. These are upgraded by LibreOffice before the real
# converter runs. (.xls is absent on purpose: xlrd and in2csv read it directly.)
LEGACY_TO_MODERN = {"doc": DOCX, "ppt": PPTX}

# What a modern container degrades to when the bytes turn out to be OLE2.
_MODERN_TO_LEGACY = {DOCX: "doc", PPTX: "ppt", XLSX: XLSX}

_BY_EXTENSION = {
    ".docx": DOCX,
    ".docm": DOCX,
    ".dotx": DOCX,
    ".pptx": PPTX,
    ".pptm": PPTX,
    ".potx": PPTX,
    ".xlsx": XLSX,
    ".xlsm": XLSX,
    ".xltx": XLSX,
    ".pdf": PDF,
    ".doc": "doc",
    ".ppt": "ppt",
    ".xls": XLSX,  # in2csv and xlrd read legacy .xls natively
}

SUPPORTED_EXTENSIONS = frozenset(_BY_EXTENSION)

# Extensions whose bytes must be a zip container to be readable at all.
_OOXML_EXTENSIONS = frozenset(
    {".docx", ".docm", ".dotx", ".pptx", ".pptm", ".potx", ".xlsx", ".xlsm", ".xltx"}
)

_ZIP_MAGIC = b"PK\x03\x04"
_PDF_MAGIC = b"%PDF-"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # .doc/.ppt/.xls compound file
_OLE2 = "ole2"

# Marker entries inside an OOXML zip, used when the extension lies.
_OOXML_MARKERS = (
    ("word/document.xml", DOCX),
    ("ppt/presentation.xml", PPTX),
    ("xl/workbook.xml", XLSX),
)


def is_ole2(path: Path) -> bool:
    """True when the file is a legacy OLE2 compound document."""
    try:
        with path.open("rb") as fh:
            return fh.read(8) == _OLE2_MAGIC
    except OSError:
        return False


def _sniff_ooxml(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return None
    for marker, kind in _OOXML_MARKERS:
        if marker in names:
            return kind
    return None


def _sniff(path: Path) -> str | None:
    """Return a kind, ``"ole2"``, or ``None`` when the bytes are unrecognised."""
    try:
        with path.open("rb") as fh:
            head = fh.read(8)
    except OSError:
        return None
    if head.startswith(_PDF_MAGIC):
        return PDF
    if head == _OLE2_MAGIC:
        return _OLE2
    if head.startswith(_ZIP_MAGIC):
        return _sniff_ooxml(path)
    return None


def detect(path: Path) -> tuple[str, str | None]:
    """Return ``(kind, warning)`` for ``path``.

    The extension is trusted first because it is cheap and almost always
    right, but it is verified against the file's magic bytes. Files renamed
    between formats are common enough -- and silently mis-converting one is
    damaging enough -- to be worth the few bytes of I/O.
    """
    suffix = path.suffix.lower()
    by_ext = _BY_EXTENSION.get(suffix)
    sniffed = _sniff(path)

    if by_ext is None:
        if sniffed in (None, _OLE2):
            # OLE2 alone cannot tell .doc from .xls without parsing the
            # directory, and there is no extension to disambiguate it.
            return UNKNOWN, None
        return sniffed, f"no usable extension; detected {sniffed} from contents"

    if sniffed == _OLE2:
        if suffix in _OOXML_EXTENSIONS:
            # The xlsx converter reads legacy workbooks itself, so its kind is
            # unchanged; doc/ppt route through LibreOffice instead.
            kind = _MODERN_TO_LEGACY[by_ext]
            label = "xls" if kind == XLSX else kind
            return kind, f"{suffix} file is really a legacy OLE2 document; reading it as .{label}"
        return by_ext, None  # .doc/.ppt/.xls, exactly as advertised

    if sniffed is None:
        if suffix in _OOXML_EXTENSIONS:
            return UNKNOWN, f"{suffix} file is not a valid zip container (truncated or corrupt)"
        if by_ext == PDF:
            return UNKNOWN, "file does not start with a PDF header (truncated or corrupt)"
        return by_ext, None  # .doc/.ppt/.xls: OLE2 check above already ran

    expected = LEGACY_TO_MODERN.get(by_ext, by_ext)
    if sniffed != expected:
        return sniffed, f"extension says {by_ext} but contents are {sniffed}; trusting contents"

    return by_ext, None
