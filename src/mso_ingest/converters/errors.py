"""Errors raised while dispatching a document to a converter."""

from __future__ import annotations


class UnsupportedDocument(RuntimeError):
    """Nothing in the pipeline can read this document."""
