#!/usr/bin/env python3
"""Read-only auditor for issue #1470 — Parquet/CNJ catalog audit.

Classifies each `comunicacoes`/`processos` Parquet file published under a
`djen-*` Internet Archive item into one of five buckets, using ONLY the
Parquet footer (row-group stats + KV metadata) — never the row data itself,
and never triggering a re-upload:

- `conformant`      — the file's KV metadata already certifies the CNJ
                       normalization/ordering contract (CONFORMANT_MARKER_KEY).
- `reorder_candidate` — no certifying marker, and the `numero_processo`
                       row-group ranges overlap, proving the file is NOT
                       sorted by CNJ.
- `verify_values`   — no certifying marker and the footer stats are
                       inconclusive (a single row group, or any row group
                       whose bounds are unreadable/null). Per the issue's own
                       acceptance criteria, non-overlapping ranges alone do
                       NOT prove normalization or internal ordering, so this
                       bucket is the safe default whenever overlap cannot be
                       positively confirmed.
- `not_applicable`  — the table has no CNJ column (e.g. `destinatarios`).
- `unavailable`     — the footer could not be read (network/IO error). This
                       is an unknown gap, not evidence either way — mirrors
                       CLAUDE.md's "never treat a fetch failure as absent"
                       rule for DJEN HTTP checks.

Usage:
    uv run python scripts/audit_cnj_parquets.py --output audit-report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx
import structlog


log = structlog.get_logger()

REORDER_CANDIDATE = "reorder_candidate"
VERIFY_VALUES = "verify_values"
CONFORMANT = "conformant"
NOT_APPLICABLE = "not_applicable"
UNAVAILABLE = "unavailable"

CNJ_COLUMN = "numero_processo"
CNJ_TABLES = frozenset({"comunicacoes", "processos"})
CONFORMANT_MARKER_KEY = "causaganha.layout"
CONFORMANT_MARKER_VALUE = "cnj-text-sorted-v1"

IA_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata/{item_id}"
IA_DOWNLOAD_URL = "https://archive.org/download/{item_id}/{filename}"

# Current IA item naming is `djen-{tribunal}-{year}` (e.g. djen-tjro-2025).
# The old `djen-YYYY-MM-DD` per-day format is discontinued (see CLAUDE.md)
# but `identifier:djen-*` still matches hundreds of those legacy items, none
# of which ever held a consolidated comunicacoes/processos.parquet.
_TRIBUNAL_YEAR_ITEM_RE = re.compile(r"^djen-[a-z-]+-\d{4}$")


def is_tribunal_year_item(item_id: str) -> bool:
    """True for the current `djen-{tribunal}-{year}` naming convention."""
    return bool(_TRIBUNAL_YEAR_ITEM_RE.match(item_id))


@dataclass(frozen=True)
class FooterStats:
    """Footer-only facts read from one Parquet file, never the row data."""

    table_name: str
    row_count: int
    row_group_ranges: list[tuple[str | None, str | None]]
    kv_metadata: dict[str, str]
    read_error: str | None = None


def ranges_overlap(ranges: list[tuple[str, str]]) -> bool:
    """True if any two (min, max) row-group ranges intersect.

    Callers must filter out any range with a None bound first — a None bound
    means "unknown", not "no constraint", and must never be treated as
    non-overlapping here.
    """
    ordered = sorted(ranges, key=lambda r: r[0])
    return any(
        next_min <= prev_max
        for (_, prev_max), (next_min, _) in zip(ordered, ordered[1:], strict=False)
    )


def classify_file(
    *,
    table_name: str,
    has_conformant_marker: bool,
    row_group_ranges: list[tuple[str | None, str | None]],
    read_error: str | None,
) -> str:
    """Classify one file per issue #1470's five buckets. See module docstring."""
    if read_error:
        return UNAVAILABLE
    if table_name not in CNJ_TABLES:
        return NOT_APPLICABLE
    if has_conformant_marker:
        return CONFORMANT
    if len(row_group_ranges) <= 1:
        return VERIFY_VALUES
    clean_ranges = [(lo, hi) for lo, hi in row_group_ranges if lo is not None and hi is not None]
    if len(clean_ranges) != len(row_group_ranges):
        return VERIFY_VALUES
    if ranges_overlap(clean_ranges):
        return REORDER_CANDIDATE
    return VERIFY_VALUES


def _read_row_count(con: duckdb.DuckDBPyConnection, path_or_url: str) -> int:
    rows = con.execute(
        f"SELECT DISTINCT row_group_id, row_group_num_rows FROM parquet_metadata('{path_or_url}')"
    ).fetchall()
    return sum(num_rows for _, num_rows in rows)


def _read_cnj_row_group_ranges(
    con: duckdb.DuckDBPyConnection, path_or_url: str
) -> list[tuple[str | None, str | None]]:
    rows = con.execute(
        "SELECT stats_min_value, stats_max_value FROM parquet_metadata(?) "
        "WHERE path_in_schema = ? ORDER BY row_group_id",
        [path_or_url, CNJ_COLUMN],
    ).fetchall()
    return [(lo, hi) for lo, hi in rows]


def _read_kv_metadata(con: duckdb.DuckDBPyConnection, path_or_url: str) -> dict[str, str]:
    rows = con.execute(f"SELECT key, value FROM parquet_kv_metadata('{path_or_url}')").fetchall()
    return {
        (k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)): (
            v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
        )
        for k, v in rows
    }


def read_footer_stats(path_or_url: str, *, table_name: str) -> FooterStats:
    """Read one Parquet file's footer only — no row data, no re-upload risk.

    DuckDB's `parquet_metadata`/`parquet_kv_metadata` table functions fetch
    just the footer via HTTP range requests for a remote URL, or a direct
    file read for a local path.
    """
    con = duckdb.connect(":memory:")
    try:
        row_count = _read_row_count(con, path_or_url)
        row_group_ranges = (
            _read_cnj_row_group_ranges(con, path_or_url) if table_name in CNJ_TABLES else []
        )
        kv_metadata = _read_kv_metadata(con, path_or_url)
    except duckdb.Error as exc:
        log.warning("audit_footer_read_failed", path=path_or_url, error=str(exc))
        return FooterStats(
            table_name=table_name,
            row_count=0,
            row_group_ranges=[],
            kv_metadata={},
            read_error=str(exc),
        )
    else:
        return FooterStats(
            table_name=table_name,
            row_count=row_count,
            row_group_ranges=row_group_ranges,
            kv_metadata=kv_metadata,
        )
    finally:
        con.close()


def list_djen_items(client: httpx.Client) -> list[str]:
    """List all `djen-*` item identifiers via IA's public advanced search.

    No `ia` CLI / credentials required — this is a read-only, unauthenticated
    lookup, matching the issue's "somente leitura" requirement.
    """
    response = client.get(
        IA_ADVANCED_SEARCH_URL,
        params={
            "q": "identifier:djen-*",
            "fl[]": "identifier",
            "rows": "9999",
            "output": "json",
        },
        timeout=30,
    )
    response.raise_for_status()
    docs = response.json().get("response", {}).get("docs", [])
    identifiers = {doc["identifier"] for doc in docs if "identifier" in doc}
    return sorted(item_id for item_id in identifiers if is_tribunal_year_item(item_id))


def list_item_cnj_table_files(client: httpx.Client, item_id: str) -> list[tuple[str, str]]:
    """Return [(table_name, download_url)] for this item's CNJ-relevant tables.

    Only enumerates `comunicacoes.parquet`/`processos.parquet` — the two
    tables this audit classifies — not every file in the item.
    """
    response = client.get(IA_METADATA_URL.format(item_id=item_id), timeout=30)
    response.raise_for_status()
    files = response.json().get("files", [])
    found: list[tuple[str, str]] = []
    for entry in files:
        name = entry.get("name", "")
        table_name = name.removesuffix(".parquet")
        if name.endswith(".parquet") and table_name in CNJ_TABLES:
            found.append((table_name, IA_DOWNLOAD_URL.format(item_id=item_id, filename=name)))
    return sorted(found)


def audit_catalog(client: httpx.Client) -> list[dict]:
    """Run the full read-only audit and return one report entry per file."""
    report: list[dict] = []
    for item_id in list_djen_items(client):
        for table_name, url in list_item_cnj_table_files(client, item_id):
            stats = read_footer_stats(url, table_name=table_name)
            has_marker = stats.kv_metadata.get(CONFORMANT_MARKER_KEY) == CONFORMANT_MARKER_VALUE
            classification = classify_file(
                table_name=table_name,
                has_conformant_marker=has_marker,
                row_group_ranges=stats.row_group_ranges,
                read_error=stats.read_error,
            )
            report.append(
                {
                    "item_id": item_id,
                    "table": table_name,
                    "url": url,
                    "row_count": stats.row_count,
                    "row_group_count": len(stats.row_group_ranges),
                    "classification": classification,
                    "kv_metadata": stats.kv_metadata,
                    "read_error": stats.read_error,
                }
            )
            log.info(
                "audited_file", item_id=item_id, table=table_name, classification=classification
            )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit-cnj-parquets-report.json"),
        help="Path to write the JSON report to.",
    )
    args = parser.parse_args(argv)

    with httpx.Client() as client:
        entries = audit_catalog(client)

    report = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "conformant_marker": f"{CONFORMANT_MARKER_KEY}={CONFORMANT_MARKER_VALUE}",
        "file_count": len(entries),
        "files": entries,
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=asdict))
    log.info("audit_report_written", path=str(args.output), file_count=len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
