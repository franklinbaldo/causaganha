r"""A-pré — snapshot current Parquets from IA before a v4 schema migration.

Creates a local archive of every consolidated Parquet so the migration is
reversible.  Without this, overwriting ``{table}.parquet`` in the IA item
destroys the v3 files with no URL-addressable recovery path.

Snapshot layout (one directory per run):
    <output_dir>/
        <timestamp>/
            <item_id>/
                comunicacoes.parquet
                advogados.parquet
                ...
            snapshot_index.json   ← manifest of what was saved + SHA-256

Usage:
    # All consolidated items (dry-run to preview)
    uv run python scripts/snapshot_parquets_for_rollback.py --dry-run

    # Snapshot everything (may take a while — parallel downloads)
    uv run python scripts/snapshot_parquets_for_rollback.py \\
        --output-dir snapshots/

    # Filter to a specific tribunal
    uv run python scripts/snapshot_parquets_for_rollback.py \\
        --tribunal tjro --output-dir snapshots/

    # Inspect what a snapshot contains
    uv run python scripts/snapshot_parquets_for_rollback.py list \\
        snapshots/2026-06-07T12-00-00/

Rollback procedure (after v4 overwrites the IA item):
    1. Copy the snapshotted {table}.parquet files back to a local output dir.
    2. Run the consolidation CLI:  causaganha reconsolidate --force
       OR upload individually with  upload_to_ia.py.
    The snapshot_index.json SHA-256s can be used to verify file integrity
    before re-uploading.

Notes:
    - Downloads are streamed to disk (no full-file RAM buffering).
    - Existing files are skipped (idempotent re-runs within the same snapshot).
    - Script exits nonzero if any download fails (404 = not found is a warning,
      not a failure; HTTP 5xx / network errors are failures).
    - This script does NOT upload to IA — it only creates a local archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog


log = structlog.get_logger()

_IA_BASE = "https://archive.org/download"
_DEFAULT_MANIFEST = Path("web/public/data/consolidation-manifest.json")

# Tables produced by consolidation (schema v3, 9 tables)
_TABLES = [
    "comunicacoes",
    "advogados",
    "advogado_nomes",
    "destinatarios",
    "comunicacao_advogados",
    "textos",
    "representacoes",
    "processos",
    "partes",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(client: httpx.Client, url: str, dest: Path) -> int:
    """Stream URL to dest.  Returns bytes written.  Raises on HTTP error."""
    with client.stream("GET", url, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            total = 0
            for chunk in r.iter_bytes(8192):
                f.write(chunk)
                total += len(chunk)
    return total


def _load_manifest_items(manifest_path: Path) -> list[dict]:
    """Return list of item dicts from the local consolidation manifest."""
    if not manifest_path.exists():
        log.error("manifest_not_found", path=str(manifest_path))
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data.get("items", [])


# ── Snapshot ─────────────────────────────────────────────────────────────────


def snapshot(
    *,
    output_dir: Path,
    manifest_path: Path = _DEFAULT_MANIFEST,
    tribunal_filter: str | None = None,
    dry_run: bool = False,
) -> Path:
    """Download all consolidated Parquets to output_dir/<timestamp>/.

    Returns the snapshot root directory (even for dry runs).
    """
    items = _load_manifest_items(manifest_path)
    if not items:
        log.error("no_items_in_manifest")
        sys.exit(1)

    if tribunal_filter:
        filt = tribunal_filter.lower()
        items = [it for it in items if filt in it.get("item_id", "").lower()]
        log.info("filtered_items", tribunal=tribunal_filter, count=len(items))

    ts = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%S")
    snap_root = output_dir / ts
    index: list[dict] = []

    print(f"Snapshot root: {snap_root}")
    print(f"Items to snapshot: {len(items)}")
    print(f"Tables per item: {len(_TABLES)}")
    print()

    if dry_run:
        for it in items:
            item_id = it["item_id"]
            print(f"  [dry-run] {item_id}  ({len(_TABLES)} tables)")
        print("\nDry run complete. Re-run without --dry-run to download.")
        return snap_root

    failures: list[tuple[str, str, str]] = []  # (item_id, table, reason)

    client = httpx.Client()
    try:
        for it in items:
            item_id = it["item_id"]
            item_dir = snap_root / item_id
            item_entry: dict = {
                "item_id": item_id,
                "schema_version": it.get("schema_version", ""),
                "layout_revision": it.get("layout_revision", ""),
                "tables": {},
            }

            tables_in_item = [t for t in _TABLES if t in (it.get("tables") or {})]
            if not tables_in_item:
                # No tables recorded in manifest — try all
                tables_in_item = _TABLES

            for table in tables_in_item:
                dest = item_dir / f"{table}.parquet"
                url = f"{_IA_BASE}/{item_id}/{table}.parquet"

                if dest.exists():
                    log.info("skipping_existing", item=item_id, table=table)
                    sha = _sha256_path(dest)
                    item_entry["tables"][table] = {
                        "bytes": dest.stat().st_size,
                        "sha256": sha,
                        "status": "existing",
                    }
                    continue

                try:
                    nbytes = _download_file(client, url, dest)
                    sha = _sha256_path(dest)
                    item_entry["tables"][table] = {
                        "bytes": nbytes,
                        "sha256": sha,
                        "status": "downloaded",
                    }
                    log.info(
                        "downloaded",
                        item=item_id,
                        table=table,
                        kb=round(nbytes / 1024, 1),
                    )
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        # Table absent from this IA item — not a failure.
                        log.warning("table_not_found_on_ia", item=item_id, table=table)
                        item_entry["tables"][table] = {"status": "not_found"}
                    else:
                        reason = f"HTTP {exc.response.status_code}"
                        log.exception(
                            "download_error",
                            item=item_id,
                            table=table,
                            status=exc.response.status_code,
                        )
                        item_entry["tables"][table] = {
                            "status": "error",
                            "http_status": exc.response.status_code,
                        }
                        failures.append((item_id, table, reason))
                except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
                    reason = str(exc)
                    log.exception("download_error", item=item_id, table=table, error=reason)
                    item_entry["tables"][table] = {"status": "error", "error": reason}
                    failures.append((item_id, table, reason))

            index.append(item_entry)
    finally:
        client.close()

    snap_root.mkdir(parents=True, exist_ok=True)
    index_path = snap_root / "snapshot_index.json"
    index_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(tz=UTC).isoformat(),
                "source_manifest": str(manifest_path),
                "items": index,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if failures:
        print(f"\n⚠  {len(failures)} download(s) failed — snapshot is INCOMPLETE:")
        for item_id, table, reason in failures:
            print(f"   {item_id}/{table}: {reason}")
        print("\nSnapshot index written to:", index_path)
        print("Do NOT proceed with v4 migration until all downloads succeed.")
        sys.exit(1)

    log.info("snapshot_complete", root=str(snap_root), items=len(index))
    print(f"\nSnapshot index written to: {index_path}")
    return snap_root


# ── Restore listing ───────────────────────────────────────────────────────────


def list_snapshot(snapshot_dir: Path) -> None:
    """Print a summary of what's in a snapshot directory."""
    index_path = snapshot_dir / "snapshot_index.json"
    if not index_path.exists():
        print(f"No snapshot_index.json found in {snapshot_dir}")
        sys.exit(1)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    print(f"Snapshot created: {data.get('created_at', 'unknown')}")
    print(f"Source manifest:  {data.get('source_manifest', 'unknown')}")
    print()
    print(f"{'Item ID':<30} {'Tables':>8} {'Bytes':>12}")
    print("-" * 55)
    for it in data.get("items", []):
        tables = it.get("tables", {})
        ok = sum(1 for t in tables.values() if t.get("status") in {"downloaded", "existing"})
        total_bytes = sum(t.get("bytes", 0) for t in tables.values())
        print(f"{it['item_id']:<30} {ok:>5}/{len(tables)} {total_bytes / 1024 / 1024:>9.1f} MiB")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="A-pré: snapshot current IA Parquets before a v4 migration"
    )
    sub = ap.add_subparsers(dest="cmd")

    # Default command: snapshot
    snap_p = sub.add_parser("snapshot", help="Download Parquets to a local snapshot (default)")
    snap_p.add_argument("--output-dir", default="snapshots", help="Root dir for snapshots")
    snap_p.add_argument(
        "--manifest", default=str(_DEFAULT_MANIFEST), help="Consolidation manifest path"
    )
    snap_p.add_argument("--tribunal", help="Filter by tribunal (substring match on item_id)")
    snap_p.add_argument("--dry-run", action="store_true", help="List what would be downloaded")

    # List command
    ls_p = sub.add_parser("list", help="Summarise a snapshot directory")
    ls_p.add_argument("snapshot_dir", help="Path to snapshot/<timestamp>/ directory")

    # Allow running without subcommand (default = snapshot)
    ap.add_argument("--output-dir", default="snapshots")
    ap.add_argument("--manifest", default=str(_DEFAULT_MANIFEST))
    ap.add_argument("--tribunal")
    ap.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()

    if args.cmd == "list":
        list_snapshot(Path(args.snapshot_dir))
    else:
        snapshot(
            output_dir=Path(args.output_dir),
            manifest_path=Path(args.manifest),
            tribunal_filter=args.tribunal,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
