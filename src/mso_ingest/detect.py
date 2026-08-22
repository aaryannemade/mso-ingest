"""Decide which converter a file should go to."""

from __future__ import annotations

from pathlib import Path

from . import kinds, magic

_BY_EXTENSION = {
    ".docx": kinds.DOCX,
    ".docm": kinds.DOCX,
    ".dotx": kinds.DOCX,
    ".pptx": kinds.PPTX,
    ".pptm": kinds.PPTX,
    ".potx": kinds.PPTX,
    ".xlsx": kinds.XLSX,
    ".xlsm": kinds.XLSX,
    ".xltx": kinds.XLSX,
    ".pdf": kinds.PDF,
    ".doc": "doc",
    ".ppt": "ppt",
    ".xls": kinds.XLSX,  # in2csv and xlrd read legacy .xls natively
}

SUPPORTED_EXTENSIONS = frozenset(_BY_EXTENSION)

# Extensions whose bytes must be a zip container to be readable at all.
_OOXML_EXTENSIONS = frozenset(
    {".docx", ".docm", ".dotx", ".pptx", ".pptm", ".potx", ".xlsx", ".xlsm", ".xltx"}
)


def detect(path: Path) -> tuple[str, str | None]:
    """Return ``(kind, warning)`` for ``path``.

    The extension is trusted first because it is cheap and almost always
    right, but it is checked against the file's magic bytes. Documents renamed
    between formats are common enough -- and mis-converting one silently is
    damaging enough -- to be worth the few bytes of I/O.
    """
    suffix = path.suffix.lower()
    by_extension = _BY_EXTENSION.get(suffix)
    sniffed = magic.sniff(path)

    if by_extension is None:
        return _without_extension(sniffed)
    if sniffed == magic.OLE2:
        return _ole2_contents(suffix, by_extension)
    if sniffed is None:
        return _unrecognised_contents(suffix, by_extension)
    return _known_contents(sniffed, by_extension)


def _without_extension(sniffed: str | None) -> tuple[str, str | None]:
    if sniffed in (None, magic.OLE2):
        # OLE2 cannot be narrowed to doc/ppt/xls without parsing the container,
        # and there is no extension here to disambiguate it.
        return kinds.UNKNOWN, None
    return sniffed, f"no usable extension; detected {sniffed} from contents"


def _ole2_contents(suffix: str, by_extension: str) -> tuple[str, str | None]:
    if suffix not in _OOXML_EXTENSIONS:
        return by_extension, None  # .doc/.ppt/.xls, exactly as advertised

    # A modern extension over legacy bytes. The xlsx converter reads legacy
    # workbooks itself so its kind is unchanged; doc and ppt route through
    # LibreOffice instead.
    kind = kinds.MODERN_TO_LEGACY[by_extension]
    label = "xls" if kind == kinds.XLSX else kind
    return kind, f"{suffix} file is really a legacy OLE2 document; reading it as .{label}"


def _unrecognised_contents(suffix: str, by_extension: str) -> tuple[str, str | None]:
    if suffix in _OOXML_EXTENSIONS:
        return kinds.UNKNOWN, f"{suffix} file is not a valid zip container (truncated or corrupt)"
    if by_extension == kinds.PDF:
        return kinds.UNKNOWN, "file does not start with a PDF header (truncated or corrupt)"
    return by_extension, None  # .doc/.ppt/.xls: the OLE2 check above already ran


def _known_contents(sniffed: str, by_extension: str) -> tuple[str, str | None]:
    expected = kinds.LEGACY_TO_MODERN.get(by_extension, by_extension)
    if sniffed != expected:
        return sniffed, (
            f"extension says {by_extension} but contents are {sniffed}; trusting contents"
        )
    return by_extension, None
