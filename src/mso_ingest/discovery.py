"""Expand the paths given on the command line into a list of documents."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .detect import SUPPORTED_EXTENSIONS


@dataclass
class Discovered:
    """The outcome of expanding the command line's paths."""

    files: list[Path] = field(default_factory=list)
    missing: list[Path] = field(default_factory=list)
    skipped_dirs: list[Path] = field(default_factory=list)


def collect(inputs: Iterable[Path], *, recursive: bool) -> Discovered:
    """Find every convertible file among ``inputs``, in a stable order.

    A file named explicitly is always taken, whatever its extension, so an
    oddly-named document can still be forced through. Directory walks are
    filtered by extension to avoid trying to convert an entire source tree.
    """
    found = Discovered()
    seen: set[Path] = set()

    for raw in inputs:
        path = raw.expanduser()

        if path.is_dir():
            if not recursive:
                found.skipped_dirs.append(path)
                continue
            candidates = _walk(path)
        elif path.is_file():
            candidates = [path]
        else:
            found.missing.append(path)
            continue

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.files.append(candidate)

    return found


def _walk(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
