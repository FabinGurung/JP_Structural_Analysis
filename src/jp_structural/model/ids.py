"""Stable ID helpers for canonical structural entities."""
from __future__ import annotations
import hashlib, re
_PREFIX = re.compile(r"^[A-Z][A-Z0-9_-]{1,15}$")
def stable_id(prefix: str, source_key: str, *, namespace: str = "jp-structural") -> str:
    prefix=prefix.upper()
    if not _PREFIX.match(prefix): raise ValueError(f"Invalid ID prefix: {prefix!r}")
    key=f"{namespace}\\0{prefix}\\0{source_key}".encode("utf-8")
    return f"{prefix}-{hashlib.sha256(key).hexdigest()[:16].upper()}"
