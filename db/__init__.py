"""Database package for SCAM JOSE PAUL (SQLite migration target)."""

from . import migrate  # noqa: F401  (convenience: from db import migrate)

__all__ = ["migrate"]
