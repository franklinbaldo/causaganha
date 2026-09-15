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
- `verify_values`   — footer stats were inconclusive AND a follow-up read of
                       the actual row values (see `read_value_order`) could
                       not settle it either (read failure). An unknown gap,
                       never guessed.
- `verified_sorted` — footer stats were inconclusive, but reading the real
                       `numero_processo` values in physical file order found
                       them non-decreasing -- genuinely CNJ-ordered even
                       without the certifying KV marker.
- `verified_unsorted` — footer stats were inconclusive, and reading the real
                       values found a genuine adjacent-row inversion -- a
                       true reorder candidate, same rollout track as
                       `reorder_candidate`.
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
VERIFIED_SORTED = "verified_sorted"
VERIFIED_UNSORTED = "verified_unsorted"
CONFORMANT = "conformant"
NOT_APPLICABLE = "not_applicable"
UNAVAILABLE = "unavailable"
NATIONAL_INDEX = "national_index"

CNJ_COLUMN = "numero_processo"
CNJ_TABLES = frozenset({"comunicacoes", "processos"})
CONFORMANT_MARKER_KEY = "causaganha.layout"
CONFORMANT_MARKER_VALUE = "cnj-text-sorted-v1"

# indice_processual.parquet (RFC 0014 M2, built by scripts/reconcile_processos.py)
# is a thin cross-source index -- one row per (numero_processo, fonte, ...) --
# not a per-tribunal comunicacoes/processos export. The reorder-candidate
# contract this audit enforces does not apply to it, so it is enumerated and
# classified separately (issue #1470: "nao regenera-lo so porque nao tem o
# marcador novo").
NATIONAL_INDEX_ITEM_ID = "causaganha-dashboard"
NATIONAL_INDEX_TABLE = "indice_processual"

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
class CnjColumnDetails:
    """Aggregated per-row-group physical detail for the CNJ column.

    Populated for issue #1470 criterion 2 ("Inspecionar tipo da coluna CNJ,
    estatisticas min/max, grupos, tamanhos, compressao, encodings, Bloom
    filters") -- purely descriptive footer facts, never used to decide the
    classification bucket itself (that stays `classify_file`'s job, driven
    only by the certifying marker and the min/max ranges).
    """

    column_type: str | None
    compression_codecs: list[str]
    encodings: list[str]
    total_compressed_size: int
    total_uncompressed_size: int
    has_bloom_filter: bool


@dataclass(frozen=True)
class FooterStats:
    """Footer-only facts read from one Parquet file, never the row data."""

    table_name: str
    row_count: int
    row_group_ranges: list[tuple[str | None, str | None]]
    kv_metadata: dict[str, str]
    read_error: str | None = None
    cnj_column_details: CnjColumnDetails | None = None


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
    """Classify one file per issue #1470's buckets. See module docstring."""
    if read_error:
        return UNAVAILABLE
    if table_name == NATIONAL_INDEX_TABLE:
        return NATIONAL_INDEX
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


def resolve_verify_values(classification: str, order_result: bool | None) -> str:
    """Refine a `VERIFY_VALUES` classification using an actual value-order read.

    Every other classification already came from a decisive footer-stats
    fact (a certifying marker, a proven overlap, an unrelated table, a read
    error) and is never re-litigated here -- this only tightens the one
    bucket footer stats alone could not decide.
    """
    if classification != VERIFY_VALUES:
        return classification
    if order_result is True:
        return VERIFIED_SORTED
    if order_result is False:
        return VERIFIED_UNSORTED
    return VERIFY_VALUES


def read_value_order(path_or_url: str) -> bool | None:
    """Read the real `numero_processo` values in physical file order.

    Unlike `read_footer_stats`, this scans actual row data (still via HTTP
    range requests for a remote URL, never triggering a re-upload) to settle
    what footer stats alone could not: whether a single-row-group (or
    null-bound) file is, in fact, already sorted by CNJ. `SET threads TO 1`
    forces a single-threaded sequential scan so row order reflects physical
    file order, not an arbitrary parallel interleaving.

    Returns `True` if the column is non-decreasing, `False` if a real
    adjacent-row inversion is found, `None` if the values could not be read
    at all -- an unknown gap, never guessed either way.
    """
    con = duckdb.connect(":memory:")
    try:
        con.execute("SET threads TO 1")
        row = con.execute(
            f"SELECT count(*) FROM ("
            f"  SELECT {CNJ_COLUMN}, lag({CNJ_COLUMN}) OVER () AS prev_value "
            f"  FROM read_parquet(?)"
            f") WHERE prev_value IS NOT NULL AND {CNJ_COLUMN} < prev_value",
            [path_or_url],
        ).fetchone()
    except duckdb.Error as exc:
        log.warning("audit_value_order_read_failed", path=path_or_url, error=str(exc))
        return None
    else:
        (inversions,) = row
        return inversions == 0
    finally:
        con.close()


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


def _aggregate_cnj_column_details(
    rows: list[tuple[str | None, str | None, str | None, int | None, int | None, int | None]],
) -> CnjColumnDetails | None:
    """Aggregate raw `parquet_metadata()` rows for the CNJ column across row groups.

    Pure aggregation, kept separate from the DuckDB query itself so it can be
    tested directly against synthetic rows (a Bloom filter, in particular, is
    not something DuckDB's own Parquet writer currently produces, so a real
    fixture can only cover the absent case).
    """
    if not rows:
        return None
    types = sorted({t for t, *_ in rows if t is not None})
    compressions = sorted({c for _, c, *_ in rows if c is not None})
    encodings: set[str] = set()
    for _, _, encoding, *_ in rows:
        if encoding:
            encodings.update(part.strip() for part in encoding.split(","))
    total_compressed = sum(compressed or 0 for _, _, _, compressed, _, _ in rows)
    total_uncompressed = sum(uncompressed or 0 for _, _, _, _, uncompressed, _ in rows)
    has_bloom_filter = any((bloom_length or 0) > 0 for *_, bloom_length in rows)
    return CnjColumnDetails(
        column_type=", ".join(types) if types else None,
        compression_codecs=compressions,
        encodings=sorted(encodings),
        total_compressed_size=total_compressed,
        total_uncompressed_size=total_uncompressed,
        has_bloom_filter=has_bloom_filter,
    )


def _read_cnj_column_details(
    con: duckdb.DuckDBPyConnection, path_or_url: str
) -> CnjColumnDetails | None:
    rows = con.execute(
        "SELECT type, compression, encodings, total_compressed_size, "
        "total_uncompressed_size, bloom_filter_length "
        "FROM parquet_metadata(?) WHERE path_in_schema = ?",
        [path_or_url, CNJ_COLUMN],
    ).fetchall()
    return _aggregate_cnj_column_details(rows)


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
        cnj_column_details = _read_cnj_column_details(con, path_or_url)
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
            cnj_column_details=cnj_column_details,
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


def list_national_index_file(client: httpx.Client) -> tuple[str, str] | None:
    """Return (table_name, download_url) for indice_processual.parquet, if published.

    `None` when the dashboard item exists but hasn't published the index yet --
    an unknown gap, not evidence it needs regeneration (same "absent is not
    unavailable" rule CLAUDE.md applies to DJEN checks).
    """
    response = client.get(IA_METADATA_URL.format(item_id=NATIONAL_INDEX_ITEM_ID), timeout=30)
    response.raise_for_status()
    files = response.json().get("files", [])
    filename = f"{NATIONAL_INDEX_TABLE}.parquet"
    if not any(entry.get("name") == filename for entry in files):
        return None
    url = IA_DOWNLOAD_URL.format(item_id=NATIONAL_INDEX_ITEM_ID, filename=filename)
    return (NATIONAL_INDEX_TABLE, url)


_REGENERATION_PLANS: dict[str, str] = {
    CONFORMANT: "no_action_already_certified",
    REORDER_CANDIDATE: "regenerate_with_cnj_text_sorted_v1_layout",
    VERIFIED_UNSORTED: "regenerate_with_cnj_text_sorted_v1_layout",
    VERIFIED_SORTED: "certify_marker_only_no_data_rewrite_needed",
    VERIFY_VALUES: "retry_value_order_check_before_deciding",
    NOT_APPLICABLE: "no_action_no_cnj_column",
    NATIONAL_INDEX: "handled_by_reconcile_processos_not_this_audit",
    UNAVAILABLE: "retry_read_unknown_gap",
}


def regeneration_plan_for(classification: str) -> str:
    """Map one classification bucket to its per-file regeneration plan.

    Issue #1470 criterion 7 ("Salvar relatorio JSON e plano por arquivo"):
    the plan is a pure function of the classification bucket already
    decided by `classify_file`/`resolve_verify_values` -- it never
    re-inspects footer stats or row data itself.
    """
    return _REGENERATION_PLANS[classification]


def _audit_file(item_id: str, table_name: str, url: str) -> dict:
    """Audit one Parquet file: footer stats, classify, then resolve verify_values."""
    stats = read_footer_stats(url, table_name=table_name)
    has_marker = stats.kv_metadata.get(CONFORMANT_MARKER_KEY) == CONFORMANT_MARKER_VALUE
    classification = classify_file(
        table_name=table_name,
        has_conformant_marker=has_marker,
        row_group_ranges=stats.row_group_ranges,
        read_error=stats.read_error,
    )
    if classification == VERIFY_VALUES:
        classification = resolve_verify_values(classification, read_value_order(url))
    log.info("audited_file", item_id=item_id, table=table_name, classification=classification)
    return {
        "item_id": item_id,
        "table": table_name,
        "url": url,
        "row_count": stats.row_count,
        "row_group_count": len(stats.row_group_ranges),
        "classification": classification,
        "regeneration_plan": regeneration_plan_for(classification),
        "kv_metadata": stats.kv_metadata,
        "cnj_column_details": stats.cnj_column_details,
        "read_error": stats.read_error,
    }


def audit_catalog(client: httpx.Client) -> list[dict]:
    """Run the full read-only audit and return one report entry per file."""
    report: list[dict] = []
    national_index = list_national_index_file(client)
    if national_index is not None:
        table_name, url = national_index
        report.append(_audit_file(NATIONAL_INDEX_ITEM_ID, table_name, url))
    for item_id in list_djen_items(client):
        for table_name, url in list_item_cnj_table_files(client, item_id):
            report.append(_audit_file(item_id, table_name, url))
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
