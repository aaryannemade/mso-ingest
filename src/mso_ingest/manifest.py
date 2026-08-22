"""The machine-readable index an agent reads instead of crawling the tree."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1

# Artifact roles.
MARKDOWN = "markdown"
CSV = "csv"
IMAGE = "image"
MEDIA = "media"

# Document statuses.
OK = "ok"
PARTIAL = "partial"  # produced output, but something was lost or guessed
ERROR = "error"


@dataclass
class Artifact:
    path: str  # relative to the output root, POSIX separators
    role: str
    bytes: int
    meta: dict = field(default_factory=dict)


@dataclass
class Document:
    source: str
    kind: str
    status: str
    output_dir: str
    source_bytes: int = 0
    sha256: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "kind": self.kind,
            "status": self.status,
            "output_dir": self.output_dir,
            "source_bytes": self.source_bytes,
            "sha256": self.sha256,
            "artifacts": [
                {
                    "path": a.path,
                    "role": a.role,
                    "bytes": a.bytes,
                    **({"meta": a.meta} if a.meta else {}),
                }
                for a in self.artifacts
            ],
            "warnings": self.warnings,
            "error": self.error,
        }


def sha256_of(path: Path, *, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def write(root: Path, documents: list[Document]) -> Path:
    counts: dict[str, int] = {}
    for doc in documents:
        counts[doc.status] = counts.get(doc.status, 0) + 1

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "documents": len(documents),
            "ok": counts.get(OK, 0),
            "partial": counts.get(PARTIAL, 0),
            "error": counts.get(ERROR, 0),
        },
        "documents": [d.as_dict() for d in documents],
    }

    dest = root / "manifest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
