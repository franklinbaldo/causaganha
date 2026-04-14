"""Read sync-manifest.csv via DuckDB — no in-memory Python materialization.

Old ``load_sync_manifest()`` built a ``dict[date, list[dict]]`` with 138K+
nested dicts (2300 dates * ~60 tribunals). That was the cheapest of three
manifest loaders but still held tens of MB of small Python objects.

Here we query the CSV directly via ``read_csv_auto`` and return iterators
or scalar counts — no Python dicts, no pandas DataFrames. DuckDB reads the
CSV with columnar layout and predicate pushdown.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import structlog


if TYPE_CHECKING:
    from collections.abc import Iterator


log = structlog.get_logger()

DEFAULT_MANIFEST_PATH = Path("data/sync-manifest.csv")


def _connect() -> duckdb.DuckDBPyConnection:
    """Create a DuckDB in-memory connection for manifest queries."""
    return duckdb.connect(":memory:")


def _csv_source(path: Path) -> str:
    """Return the SQL fragment for reading the manifest CSV via DuckDB."""
    # read_csv_auto handles the header automatically; use single-quote escaping.
    return f"read_csv_auto('{path.as_posix()}')"


def dates_with_uploads(
    path: Path = DEFAULT_MANIFEST_PATH,
) -> Iterator[str]:
    """Yield date strings that have at least one ``ia_status='uploaded'`` row.

    Uses DuckDB to do the scan + filter + distinct without bringing the rows
    into Python. Results yield as strings in ISO format (YYYY-MM-DD).
    """
    if not path.exists():
        log.info("sync_manifest_not_found", path=str(path))
        return
    con = _connect()
    try:
        query = f"""
            SELECT DISTINCT CAST(date AS VARCHAR) AS date_str
            FROM {_csv_source(path)}
            WHERE ia_status = 'uploaded'
            ORDER BY date_str DESC
        """
        for row in con.execute(query).fetchall():
            yield str(row[0])
    finally:
        con.close()


def uploaded_zips_for_date(
    date_str: str,
    path: Path = DEFAULT_MANIFEST_PATH,
) -> list[dict[str, Any]]:
    """Return the uploaded ZIP entries for a given date (one per tribunal).

    This is the only query that returns rows — by design bounded to one date's
    worth of tribunals (~60 dicts), not the full manifest.
    """
    if not path.exists():
        return []
    con = _connect()
    try:
        query = f"""
            SELECT tribunal, CAST(date AS VARCHAR)
            FROM {_csv_source(path)}
            WHERE date = CAST(? AS DATE) AND ia_status = 'uploaded'
            ORDER BY tribunal
        """
        rows = con.execute(query, [date_str]).fetchall()
    finally:
        con.close()

    return [
        {
            "tribunal": tribunal,
            "item_id": f"djen-{tribunal.lower()}-{date_str[:4]}",
            "filename": f"djen-{date_str}-{tribunal}.zip",
            "absent": False,
        }
        for tribunal, _ in rows
    ]


def uploaded_zips_for_tribunal_year(
    tribunal: str,
    year: int,
    path: Path = DEFAULT_MANIFEST_PATH,
) -> list[dict[str, Any]]:
    """Return all uploaded ZIP entries for a (tribunal, year) pair.

    Rows are bounded to one tribunal-year (~260 business days) so the
    materialization is small.
    """
    if not path.exists():
        return []
    con = _connect()
    try:
        query = f"""
            SELECT CAST(date AS VARCHAR) AS date_str
            FROM {_csv_source(path)}
            WHERE tribunal = ?
              AND EXTRACT(year FROM date) = ?
              AND ia_status = 'uploaded'
            ORDER BY date
        """
        rows = con.execute(query, [tribunal.upper(), year]).fetchall()
    finally:
        con.close()

    item_id = f"djen-{tribunal.lower()}-{year}"
    return [
        {
            "tribunal": tribunal.upper(),
            "item_id": item_id,
            "filename": f"djen-{row[0]}-{tribunal.upper()}.zip",
            "absent": False,
        }
        for row in rows
    ]


def counts_summary(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, int]:
    """Return top-level counts (uploaded, absent, total) — for logging only."""
    if not path.exists():
        return {"uploaded": 0, "absent": 0, "total": 0}
    con = _connect()
    try:
        query = f"""
            SELECT
                SUM(CASE WHEN ia_status = 'uploaded' THEN 1 ELSE 0 END) AS uploaded,
                SUM(CASE WHEN djen_status = 'absent' THEN 1 ELSE 0 END) AS absent,
                COUNT(*) AS total
            FROM {_csv_source(path)}
        """
        uploaded, absent, total = con.execute(query).fetchone()
    finally:
        con.close()

    return {
        "uploaded": int(uploaded or 0),
        "absent": int(absent or 0),
        "total": int(total or 0),
    }
