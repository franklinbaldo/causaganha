"""Find dates / (tribunal, year) pairs needing consolidation.

Previously ``fetch_manifest_records()`` loaded the entire IA ``manifest.parquet``
(often 100+ MB) into a pandas DataFrame, then converted to a list of dicts —
which was the most likely OOM trigger on constrained machines.

Here we use DuckDB + ``httpfs`` to query the remote Parquet directly, pushing
aggregations into DuckDB so only the aggregated result set reaches Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import structlog


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


log = structlog.get_logger()

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
              AND file_type = 'zip'
            GROUP BY item_id, tribunal, year
            HAVING SUM(
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
