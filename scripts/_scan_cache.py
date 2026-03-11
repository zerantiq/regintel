"""Shared helpers for incremental scan caching and parallel worker defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def default_parallel_workers(cap: int = 8) -> int:
    """Return a bounded default worker count for predictable host utilization."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cap, cpu_count))


def file_fingerprint(path: Path) -> str:
    """Return a stable content-change fingerprint from file metadata."""
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def load_scan_cache(cache_file: Path, *, version: str) -> dict[str, dict[str, Any]]:
    """Load a versioned cache entry map from disk.

    Returns an empty map when the cache file is missing, unreadable, or stale.
    """
    if not cache_file.exists():
        return {}
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if payload.get("version") != version:
        return {}
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return {}
    return entries


def save_scan_cache(
    cache_file: Path, *, version: str, entries: dict[str, dict[str, Any]]
) -> None:
    """Persist cache entries atomically, ignoring non-fatal filesystem errors."""
    payload = {"version": version, "entries": entries}
    tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        tmp_file.replace(cache_file)
    except OSError:
        return

