"""Wrappers around the external CLI tools the converters shell out to.

One module per binary. Every wrapper raises :class:`ToolError` on failure, so
a caller can choose between falling back to another engine and recording a
warning against the document.
"""

from .process import ToolError

__all__ = ["ToolError"]
