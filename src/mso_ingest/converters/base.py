"""Shared plumbing for the per-format converters."""

from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from ..manifest import Artifact

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class Context:
    """Everything a converter needs to know about one job."""

    source: Path
    outdir: Path  # per-document directory, already created
    stem: str  # sanitised base name for primary artifacts
    dpi: int = 150
    ocr: bool = True
    ocr_lang: str = "eng"


@dataclass
class Result:
    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False  # output exists but is known to be lossy

    def add(self, path: Path, role: str, *, root: Path, meta: dict | None = None) -> None:
        if not path.exists():
            return
        self.artifacts.append(
            Artifact(
                path=path.relative_to(root).as_posix(),
                role=role,
                bytes=path.stat().st_size,
                meta=meta or {},
            )
        )

    def warn(self, message: str, *, degraded: bool = False) -> None:
        self.warnings.append(message)
        if degraded:
            self.degraded = True


def sanitize(name: str, *, fallback: str = "untitled") -> str:
    """Reduce an arbitrary label (sheet name, filename) to a safe path segment.

    Accents are folded rather than dropped, so a sheet called ``Ünïcode`` lands
    at ``Unicode`` instead of the unreadable ``n-code``. Scripts with no ASCII
    equivalent collapse away entirely and fall back to a positional name; the
    manifest always carries the original label.
    """
    folded = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in folded if not unicodedata.combining(ch))
    cleaned = _UNSAFE.sub("-", ascii_only).strip("-._")
    return cleaned[:120] or fallback


def unique(name: str, taken: set[str]) -> str:
    """Return ``name`` made unique against ``taken``, registering the result."""
    candidate, index = name, 2
    while candidate.lower() in taken:
        candidate = f"{name}-{index}"
        index += 1
    taken.add(candidate.lower())
    return candidate


def reset_dir(path: Path) -> Path:
    """Create ``path`` empty, dropping stale artifacts from a previous run.

    Only ever called on directories this tool created inside the output root.
    """
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path
