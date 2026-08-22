"""``.xlsx`` / ``.xls`` -> one CSV per worksheet, in workbook order."""

from __future__ import annotations

from .. import magic
from ..manifest import CSV
from ..paths import reset_dir, sanitize, unique
from ..tools import ToolError, csvkit
from . import sheets
from .context import Context, Result


def convert(ctx: Context) -> Result:
    result = Result()

    # Decided by content, not extension: legacy workbooks renamed to .xlsx are
    # common, and openpyxl cannot read them.
    legacy = magic.is_ole2(ctx.source)

    try:
        found = sheets.describe(ctx.source, legacy=legacy)
    except Exception as exc:  # noqa: BLE001 - surfaced as a per-document error
        result.warn(f"could not read workbook structure: {exc}", degraded=True)
        return result

    if not found:
        result.warn("workbook contains no worksheets", degraded=True)
        return result

    sheets_dir = reset_dir(ctx.outdir / "sheets")
    taken: set[str] = set()

    for index, sheet in enumerate(found, start=1):
        # Sheet names allow characters filenames do not, and two of them can
        # sanitise to the same string, so uniqueness is enforced here.
        filename = unique(sanitize(sheet.name, fallback=f"sheet-{index}"), taken)
        dest = sheets_dir / f"{filename}.csv"

        try:
            csvkit.sheet_to_csv(ctx.source, sheet.name, dest, fmt="xls" if legacy else None)
        except ToolError as exc:
            result.warn(f"sheet {sheet.name!r} failed to convert: {exc}", degraded=True)
            dest.unlink(missing_ok=True)
            continue

        result.add(
            dest,
            CSV,
            root=ctx.root,
            meta={
                "sheet": sheet.name,
                "index": index,
                "rows": sheet.rows,
                "columns": sheet.columns,
            },
        )

    return result
