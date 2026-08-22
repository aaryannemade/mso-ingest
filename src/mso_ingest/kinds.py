"""The document kinds the rest of the package dispatches on."""

from __future__ import annotations

DOCX = "docx"
PPTX = "pptx"
XLSX = "xlsx"
PDF = "pdf"
UNKNOWN = "unknown"

# Legacy binary formats, upgraded by LibreOffice before the real converter
# runs. (.xls is absent on purpose: xlrd and in2csv read it directly.)
LEGACY_TO_MODERN = {"doc": DOCX, "ppt": PPTX}

# What a modern container degrades to when its bytes turn out to be OLE2.
MODERN_TO_LEGACY = {DOCX: "doc", PPTX: "ppt", XLSX: XLSX}
