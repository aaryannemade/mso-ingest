"""What a converter is given, and what it hands back."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..manifest import Artifact


@dataclass(frozen=True)
class Context:
    """Everything a converter needs to know about one document."""

    source: Path
    outdir: Path  # per-document directory, already created
    stem: str  # sanitised base name for primary artifacts
    dpi: int = 150
    ocr: bool = True
    ocr_lang: str = "eng"

    @property
    def root(self) -> Path:
        """The output root, which artifact paths are recorded relative to."""
        return self.outdir.parent


@dataclass
class Result:
    """Artifacts produced for one document, plus anything worth flagging."""

    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False  # output exists, but is known to be lossy

    def add(self, path: Path, role: str, *, root: Path, meta: dict | None = None) -> None:
        """Record ``path`` as an artifact, ignoring it if it was never written."""
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
        """Note a problem. ``degraded`` marks the whole document as partial."""
        self.warnings.append(message)
        if degraded:
            self.degraded = True
