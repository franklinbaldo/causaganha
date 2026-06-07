"""Phase 0.6: Consolidation manifest — single JSON tracking all consolidated Parquets.

Modelled on ficha ADR 0008. Written to web/public/data/consolidation-manifest.json
(or a caller-supplied path) after each successful date consolidation.

Consumers:
  - Frontend (one fetch at boot to discover all available Parquets + schema version)
  - CI drift-detection (diff successive manifests for row-count drops)
  - DuckDB WASM (reads schema_version from manifest before opening Parquet)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import structlog


log = structlog.get_logger()

_DEFAULT_MANIFEST_PATH = Path("web/public/data/consolidation-manifest.json")


@dataclass
class TableStats:
    """Per-table statistics embedded in each manifest item."""

    rows: int
    size_bytes: int
    sha256: str


@dataclass
class ManifestItem:
    """One consolidated date in the manifest."""

    item_id: str
    date: str
    schema_version: str
    layout_revision: str
    tables: dict[str, dict]
    consolidated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


def collect_table_stats(
    output_dir: Path,
    table_names: list[str],
) -> dict[str, TableStats]:
    """Compute row count, file size, and SHA-256 for each exported Parquet.

    Only includes tables whose Parquet file exists in output_dir.
    """
    stats: dict[str, TableStats] = {}
    con = duckdb.connect()
    try:
        for name in table_names:
            path = output_dir / f"{name}.parquet"
            if not path.exists():
                continue
            rows = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
            size = path.stat().st_size
            sha = _sha256_file(path)
            stats[name] = TableStats(rows=rows, size_bytes=size, sha256=sha)
    finally:
        con.close()
    return stats


def update_consolidation_manifest(
    item_id: str,
    date_str: str,
    schema_version: str,
    table_stats: dict[str, TableStats],
    *,
    layout_revision: str = "",
    manifest_path: Path = _DEFAULT_MANIFEST_PATH,
) -> None:
    """Read, merge, and write the consolidation manifest.

    Creates the manifest if it doesn't exist. Replaces any existing entry
    for item_id so re-runs are idempotent. Items are kept sorted by date.
    """
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"schema_version": schema_version, "items": []}

    manifest["items"] = [it for it in manifest["items"] if it.get("item_id") != item_id]

    entry = ManifestItem(
        item_id=item_id,
        date=date_str,
        schema_version=schema_version,
        layout_revision=layout_revision,
        tables={name: asdict(s) for name, s in table_stats.items()},
    )
    manifest["items"].append(asdict(entry))
    manifest["items"].sort(key=lambda it: it["date"])
    manifest["generated_at"] = datetime.now(tz=UTC).isoformat()

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info(
        "manifest_updated",
        item_id=item_id,
        tables=len(table_stats),
        path=str(manifest_path),
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
