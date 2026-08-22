"""Everything this tool prints to the terminal.

Progress goes to stderr so that stdout stays free for future machine-readable
output, and so redirecting it never mixes with the converted documents.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from . import manifest, pipeline
from .discovery import Discovered

_STATUS_COLOUR = {
    manifest.OK: "green",
    manifest.PARTIAL: "yellow",
    manifest.ERROR: "red",
}


class Reporter:
    """Prints progress. ``quiet`` suppresses everything but problems."""

    def __init__(self, *, quiet: bool = False, console: Console | None = None) -> None:
        self.quiet = quiet
        self.console = console or Console(stderr=True)

    def discovery(self, found: Discovered) -> None:
        for directory in found.skipped_dirs:
            self.console.print(f"[yellow]skipping directory[/] {directory} (use --recursive)")
        for path in found.missing:
            self.console.print(f"[red]no such path[/] {path}")

    def nothing_to_convert(self) -> None:
        self.console.print("[red]nothing to convert[/]")

    def outcome(self, outcome: pipeline.Outcome) -> None:
        document = outcome.document

        # Problems are always reported, even when quiet.
        if outcome.stage == pipeline.UNSUPPORTED:
            self.console.print(f"[red]skip[/] {document.source} ({document.error})")
        elif outcome.stage == pipeline.CRASHED:
            self.console.print(f"[red]fail[/] {document.source}: {document.error}")
        elif not self.quiet:
            self.console.print(self._summary_line(document))

        for warning in document.warnings:
            self.console.print(f"  [yellow]warn[/] {warning}")

    def manifest_written(self, path: Path) -> None:
        if not self.quiet:
            self.console.print(f"\nmanifest: {path}")

    def failures(self, failed: int, total: int) -> None:
        self.console.print(f"[red]{failed} of {total} document(s) failed[/]")

    def _summary_line(self, document: manifest.Document) -> str:
        colour = _STATUS_COLOUR[document.status]
        count = len(document.artifacts)
        plural = "" if count == 1 else "s"
        return (
            f"[{colour}]{document.status}[/] {document.source} -> "
            f"{document.output_dir}/ ({count} artifact{plural})"
        )
