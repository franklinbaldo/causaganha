"""Query the canonical manifest parquet plus pending event-log segments.

The dashboard's ``sync-manifest.parquet`` is a compacted base, not a complete
snapshot while ``manifest-log/*.csv`` exists.  This module deliberately uses
the same replay implementation as ``SyncManifest.load_from_ia`` so local
consumers observe a newly uploaded segment before the next compaction.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from djen_backup.manifest import load_materialized_manifest


if TYPE_CHECKING:
    from collections.abc import Iterator

    from djen_backup.manifest import ManifestEntry, SyncManifest


log = structlog.get_logger()

DEFAULT_MANIFEST_PATH = Path("data/sync-manifest.parquet")
DEFAULT_SEGMENT_DIR = Path("data/manifest-log")


def _manifest(path: Path, segment_dir: Path | None = None) -> SyncManifest:
    """Return the local parquet base with pending segments replayed."""
    segments = segment_dir if segment_dir is not None else path.parent / "manifest-log"
    if not path.exists():
        log.info("sync_manifest_parquet_not_found", path=str(path))
    return load_materialized_manifest(path, segments)


def entries(path: Path = DEFAULT_MANIFEST_PATH) -> list[ManifestEntry]:
    """Return entries from the canonical base with pending segments replayed."""
    return _manifest(path).all_entries()


def dates_with_uploads(path: Path = DEFAULT_MANIFEST_PATH) -> Iterator[str]:
    """Yield uploaded dates, newest first, including un-compacted updates."""
    entries = _manifest(path).all_entries()
    yield from sorted(
        {entry.date.isoformat() for entry in entries if entry.ia_status == "uploaded"}, reverse=True
    )


def uploaded_zips_for_date(
    date_str: str, path: Path = DEFAULT_MANIFEST_PATH
) -> list[dict[str, Any]]:
    """Return uploaded ZIP entries for one date after replaying pending segments."""
    return [
        {
            "tribunal": entry.tribunal,
            "item_id": f"djen-{entry.tribunal.lower()}-{entry.date.year}",
            "filename": f"djen-{entry.date.isoformat()}-{entry.tribunal}.zip",
            "absent": False,
        }
        for entry in _manifest(path).all_entries()
        if entry.date.isoformat() == date_str and entry.ia_status == "uploaded"
    ]


def uploaded_zips_for_tribunal_year(
    tribunal: str, year: int, path: Path = DEFAULT_MANIFEST_PATH
) -> list[dict[str, Any]]:
    """Return uploaded ZIP entries for a tribunal-year including pending updates."""
    tribunal = tribunal.upper()
    return [
        {
            "tribunal": tribunal,
            "item_id": f"djen-{tribunal.lower()}-{year}",
            "filename": f"djen-{entry.date.isoformat()}-{tribunal}.zip",
            "absent": False,
        }
        for entry in _manifest(path).all_entries()
        if entry.tribunal == tribunal and entry.date.year == year and entry.ia_status == "uploaded"
    ]


def counts_summary(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, int]:
    """Return manifest status counts after replaying pending segments."""
    entries = _manifest(path).all_entries()
    return {
        "uploaded": sum(entry.ia_status == "uploaded" for entry in entries),
        "absent": sum(entry.djen_status == "absent" for entry in entries),
        "total": len(entries),
    }
