"""csvkit's ``in2csv``."""

from __future__ import annotations

from pathlib import Path

from .process import require, run


def sheet_to_csv(src: Path, sheet: str, dest: Path, *, fmt: str | None = None) -> None:
    """Extract a single worksheet from ``src`` to ``dest``.

    Two csvkit behaviours are worked around here:

    * ``--write-sheets`` writes its output next to the *input* file, which
      would scribble into the user's source tree. One ``--sheet`` at a time
      redirected to a chosen path keeps everything inside the output root.
    * Type inference is lossy. A column holding only ``0``/``1`` is inferred
      as boolean, so ``1`` lands in the CSV as ``True``. ``-I`` turns it off
      and cells survive verbatim.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [require("in2csv"), "-I", "--sheet", sheet]
    if fmt:
        cmd += ["-f", fmt]
    cmd += [str(src)]

    run(cmd, stdout_path=dest)
