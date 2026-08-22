"""Running external commands, and the error every tool wrapper raises."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 900


class ToolError(RuntimeError):
    """An external tool is missing, timed out, or exited non-zero."""


def require(name: str) -> str:
    """Return the absolute path to ``name``, raising if it is not installed."""
    path = shutil.which(name)
    if path is None:
        raise ToolError(f"required tool {name!r} was not found on PATH")
    return path


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    stdout_path: Path | None = None,
) -> str:
    """Run ``cmd``, returning its stdout as text.

    When ``stdout_path`` is given the output is streamed to that file instead
    and the return value is empty -- some of these tools emit whole documents
    on stdout, which is not worth buffering in memory.
    """
    require(cmd[0])

    sink = stdout_path.open("wb") if stdout_path is not None else None
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            stdout=sink if sink is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{cmd[0]} timed out after {timeout}s") from exc
    finally:
        if sink is not None:
            sink.close()

    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise ToolError(f"{cmd[0]} exited {proc.returncode}: {detail[:800]}")

    return (proc.stdout or b"").decode("utf-8", "replace") if sink is None else ""
