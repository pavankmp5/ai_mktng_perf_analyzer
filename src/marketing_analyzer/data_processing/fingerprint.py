"""Input file fingerprints and comparison helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def fingerprint_file(path: Path, row_count: int, column_count: int) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "filename": path.name,
        "sha256": digest.hexdigest(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "row_count": row_count,
        "column_count": column_count,
    }


def change_status(previous: dict | None, current: dict, key: str) -> dict:
    old = (previous or {}).get(key)
    if old is None:
        return {"status": "initial_run", "changed": True, "previous_sha256": None, "current_sha256": current["sha256"]}
    changed = old.get("sha256") != current.get("sha256")
    return {"status": "changed" if changed else "unchanged", "changed": changed, "previous_sha256": old.get("sha256"), "current_sha256": current["sha256"]}
