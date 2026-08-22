"""Turning arbitrary labels into safe output paths."""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SEGMENT = 120


def sanitize(name: str, *, fallback: str = "untitled") -> str:
    """Reduce an arbitrary label (sheet name, filename) to a safe path segment.

    Accents are folded rather than dropped, so a sheet called ``Ünïcode`` lands
    at ``Unicode`` instead of the unreadable ``n-code``. Scripts with no ASCII
    equivalent collapse away entirely and fall back to a positional name; the
    manifest always carries the original label.
    """
    folded = unicodedata.normalize("NFKD", name)
    unaccented = "".join(ch for ch in folded if not unicodedata.combining(ch))
    cleaned = _UNSAFE.sub("-", unaccented).strip("-._")
    return cleaned[:_MAX_SEGMENT] or fallback


def unique(name: str, taken: set[str]) -> str:
    """Return ``name`` made unique against ``taken``, registering the result.

    Comparison is case-insensitive so the result is still unique once written
    to a case-insensitive filesystem.
    """
    candidate, index = name, 2
    while candidate.lower() in taken:
        candidate = f"{name}-{index}"
        index += 1
    taken.add(candidate.lower())
    return candidate


def reset_dir(path: Path) -> Path:
    """Create ``path`` empty, dropping artifacts left by a previous run.

    Only ever called on directories this tool itself created inside the output
    root, never on anything the user supplied.
    """
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path
