"""Find dates / (tribunal, year) pairs needing consolidation.

Previously ``fetch_manifest_records()`` loaded the entire IA ``manifest.parquet``
(often 100+ MB) into a pandas DataFrame, then converted to a list of dicts —
which was the most likely OOM trigger on constrained machines.

Here we use DuckDB + ``httpfs`` to query the remote Parquet directly, pushing
aggregations into DuckDB so only the aggregated result set reaches Python.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import structlog

from causaganha.consolidate.schema_registry import CURRENT_LAYOUT_REVISION, CURRENT_VERSION


if TYPE_CHECKING:
    from collections.abc import Iterator


log = structlog.get_logger()

_DEFAULT_CONSOLIDATION_MANIFEST = "web/public/data/consolidation-manifest.json"

IA_MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.parquet"


def _connect_httpfs() -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with httpfs loaded for remote Parquet reads."""
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


def dates_needing_consolidation_from_ia(
    manifest_url: str = IA_MANIFEST_URL,
) -> list[str]:
    """Dates with at least one ZIP but no Parquet yet (from IA manifest).

    Query is pushed to DuckDB: GROUP BY + HAVING happens remotely, Python
    only sees the aggregated dates list. Memory stays bounded regardless
    of manifest.parquet size.

    Returns dates sorted descending (newest first).
    """
    con = _connect_httpfs()
    try:
        query = f"""
            SELECT CAST(date AS VARCHAR) AS date_str
            FROM read_parquet('{manifest_url}')
            GROUP BY date
            HAVING SUM(CASE WHEN file_type='zip' THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN file_type='parquet' THEN 1 ELSE 0 END) = 0
            ORDER BY date_str DESC
        """
        rows = con.execute(query).fetchall()
    except duckdb.Error as e:
        log.warning("candidates_query_failed", error=str(e))
        return []
    finally:
        con.close()

    return [str(r[0]) for r in rows]


def tribunal_years_needing_consolidation_from_ia(
    manifest_url: str = IA_MANIFEST_URL,
) -> list[tuple[str, int]]:
    """(tribunal, year) pairs with ZIPs but no consolidated Parquet set.

    Uses the per-tribunal-year items (``djen-{tribunal}-{year}``). An item
    is considered consolidated when it has the ``_consolidated.marker``
    file (or the 10 Parquet tables).
    """
    con = _connect_httpfs()
    try:
        query = f"""
            SELECT
                split_part(item_id, '-', -2) AS tribunal,
                CAST(split_part(item_id, '-', -1) AS INTEGER) AS year
            FROM read_parquet('{manifest_url}')
            WHERE item_id LIKE 'djen-%-%'
            GROUP BY item_id, tribunal, year
            HAVING SUM(CASE WHEN file_type = 'zip' THEN 1 ELSE 0 END) > 0
               AND SUM(
                   CASE WHEN file_type = 'parquet' OR file_name = '_consolidated.marker'
                        THEN 1 ELSE 0 END
               ) = 0
            ORDER BY year DESC, tribunal
        """
        rows = con.execute(query).fetchall()
    except duckdb.Error as e:
        log.warning("candidates_tribunal_year_query_failed", error=str(e))
        return []
    finally:
        con.close()

    return [(str(t).upper(), int(y)) for t, y in rows if t and y]


def dates_needing_consolidation_from_local_manifest(
    sync_manifest_path: Path,
) -> Iterator[str]:
    """Fallback: use sync-manifest.csv when IA manifest is unavailable.

    Yields every date that has uploaded entries. The caller must check
    the consolidation checkpoint / IA markers to filter out already-done dates.
    """
    from causaganha.consolidate.manifest_reader import dates_with_uploads

    return dates_with_uploads(sync_manifest_path)


def _load_consolidated_items(
    manifest_path: str = _DEFAULT_CONSOLIDATION_MANIFEST,
) -> dict[str, dict[str, str]]:
    """Read consolidation manifest, return {date: {schema_version, layout_revision}}.

    Returns an empty dict if the manifest doesn't exist or can't be parsed.
    Missing fields default to empty string (old manifests lack layout_revision).
    """
    path = Path(manifest_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            item["date"]: {
                "schema_version": item.get("schema_version", ""),
                "layout_revision": item.get("layout_revision", ""),
            }
            for item in data.get("items", [])
            if "date" in item
        }
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        log.warning("consolidation_manifest_read_failed", error=str(exc))
        return {}


def load_consolidated_versions(
    manifest_path: str = _DEFAULT_CONSOLIDATION_MANIFEST,
) -> dict[str, str]:
    """Return {date: schema_version} for all consolidated items."""
    return {d: v["schema_version"] for d, v in _load_consolidated_items(manifest_path).items()}


def dates_at_current_version(
    manifest_path: str = _DEFAULT_CONSOLIDATION_MANIFEST,
) -> set[str]:
    """Return dates at both CURRENT_VERSION and CURRENT_LAYOUT_REVISION.

    Only these dates are truly up-to-date — stale layout_revision means the
    physical Parquet layout needs refreshing even if the schema hasn't changed.
    """
    items = _load_consolidated_items(manifest_path)
    return {
        d
        for d, info in items.items()
        if info["schema_version"] == CURRENT_VERSION
        and info["layout_revision"] == CURRENT_LAYOUT_REVISION
    }


def dates_needing_reconsolidation(
    manifest_path: str = _DEFAULT_CONSOLIDATION_MANIFEST,
) -> list[str]:
    """Return dates with stale schema_version OR stale layout_revision, newest first.

    Includes legacy items whose manifest has no layout_revision key (treated as "").
    """
    items = _load_consolidated_items(manifest_path)
    stale = [
        d
        for d, info in items.items()
        if (info["schema_version"] and info["schema_version"] != CURRENT_VERSION)
        or info["layout_revision"] != CURRENT_LAYOUT_REVISION
    ]
    stale.sort(reverse=True)
    return stale


def all_consolidated_dates(
    manifest_path: str = _DEFAULT_CONSOLIDATION_MANIFEST,
) -> list[str]:
    """Return all consolidated dates (stale or current), newest first.

    Used by ``reconsolidate --force`` to re-process even up-to-date items.
    """
    items = _load_consolidated_items(manifest_path)
    return sorted(items.keys(), reverse=True)
