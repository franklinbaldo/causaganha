#!/usr/bin/env python3
"""Local pilot validation for issue #1471 — TJRO 2026 `comunicacoes.parquet`.

Downloads the currently published `djen-tjro-2026/comunicacoes.parquet`,
regenerates it locally with the unified writer from PR #1473
(`causaganha.consolidate.exporter.export_table_sync`, layout_revision=2), and
compares old vs. candidate: row counts, identifier set, CNJ normalization
contract, untouched fields, footer KV metadata, compression, row-group
ordering and a spot check for a specific CNJ named in the issue.

This covers the *local* slice of #1471's acceptance criteria only — preserve
identity/hash, generate candidate, diff counts/identifiers/fields, verify
ordering/stats/schema/compression/footer, spot-check a named CNJ. It does
NOT cover DuckDB-native/WASM query latency measurement or an Internet
Archive publish/read-back proof — those need a real upload and are left to
a follow-up round.

Usage:
    uv run python scripts/validate_pilot_tjro_2026.py --output pilot-report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import httpx
import ibis
import structlog

from causaganha.consolidate.exporter import export_table_sync
from scripts.audit_cnj_parquets import ranges_overlap


log = structlog.get_logger()

ITEM_ID = "djen-tjro-2026"
TABLE_NAME = "comunicacoes"
SOURCE_URL = f"https://archive.org/download/{ITEM_ID}/{TABLE_NAME}.parquet"
SPOT_CHECK_CNJ = "7008332-16.2026.8.22.0007"

EXPECTED_KV_METADATA = {
    "causaganha.schema_version": "3.0.0",
    "causaganha.item_id": ITEM_ID,
    "causaganha.layout": "cnj-text-sorted-v1",
    "causaganha.cnj_normalization": "valid-20-digits-v1",
}


@dataclass(frozen=True)
class PilotReport:
    """Result of comparing the published file against the candidate rewrite."""

    item_id: str
    table_name: str
    old_url: str
    old_sha256: str
    old_row_count: int
    candidate_row_count: int
    row_count_matches: bool
    id_set_matches: bool
    normalized_value_count: int
    normalization_contract_violations: int
    other_fields_untouched: bool
    candidate_footer_boundary_ties: bool
    candidate_sort_violations: int
    candidate_compression_codecs: list[str]
    candidate_kv_metadata: dict[str, str]
    kv_metadata_matches_expected: bool
    spot_check_cnj: str
    spot_check_old_matches: int
    spot_check_candidate_matches: int
    spot_check_agrees: bool
    passed: bool
    errors: list[str]


def download_old_parquet(dest: Path) -> str:
    """Stream the currently published file to ``dest``, return its sha256 hex digest."""
    hasher = hashlib.sha256()
    with (
        httpx.stream("GET", SOURCE_URL, timeout=120, follow_redirects=True) as response,
        dest.open("wb") as fh,
    ):
        response.raise_for_status()
        for chunk in response.iter_bytes(1024 * 1024):
            hasher.update(chunk)
            fh.write(chunk)
    return hasher.hexdigest()


def build_candidate(old_path: Path, output_dir: Path) -> Path:
    """Load the old file into DuckDB and regenerate it with the unified writer."""
    con = ibis.duckdb.connect(":memory:")
    con.raw_sql(f"CREATE TABLE {TABLE_NAME} AS SELECT * FROM read_parquet('{old_path.as_posix()}')")
    result = export_table_sync(TABLE_NAME, con, output_dir, item_id=ITEM_ID)
    if result is None:
        msg = f"export_table_sync returned None for a non-empty source table at {old_path}"
        raise RuntimeError(msg)
    candidate_path, _size_mb, _count = result
    return candidate_path


def _footer_boundary_ties(con: duckdb.DuckDBPyConnection, path: Path) -> bool:
    """True if any two row groups touch at the numero_processo boundary.

    Thin wrapper around ``scripts/audit_cnj_parquets.py``'s conservative,
    already-tested ``ranges_overlap`` (any ``next_min <= prev_max`` counts):
    footer stats alone cannot distinguish "actually unsorted" from "a
    repeated CNJ legitimately spans the boundary between two row groups", so
    that script treats a touching boundary as unproven rather than as proof
    of order. This is informational context alongside the row-level
    ``_sort_violations`` check below, which resolves the ambiguity directly
    against the data instead of guessing from footer stats.
    """
    rows = con.execute(
        "SELECT stats_min_value, stats_max_value FROM parquet_metadata(?) "
        "WHERE path_in_schema = 'numero_processo' ORDER BY row_group_id",
        [path.as_posix()],
    ).fetchall()
    ranges = [(lo, hi) for lo, hi in rows if lo is not None and hi is not None]
    if len(ranges) != len(rows) or len(ranges) <= 1:
        return False
    return ranges_overlap(ranges)


def _sort_violations(con: duckdb.DuckDBPyConnection, path: Path) -> int:
    """Count rows where the file's true physical order breaks the ORDER BY contract.

    Uses DuckDB's ``file_row_number`` to read the file's actual on-disk row
    order (not a re-derived sort), so this is a definitive check of the
    ``numero_processo, data_disponibilizacao, id`` contract in
    ``exporter._TABLE_ORDER_KEYS["comunicacoes"]`` — unlike footer min/max
    stats, it is not ambiguous about ties at row-group boundaries.
    """
    return con.execute(
        f"""
        WITH ordered AS (
            SELECT numero_processo, data_disponibilizacao, id, file_row_number AS rn
            FROM read_parquet('{path.as_posix()}', file_row_number = true)
        ),
        lagged AS (
            SELECT
                numero_processo,
                data_disponibilizacao,
                lag(numero_processo) OVER (ORDER BY rn) AS prev_np,
                lag(data_disponibilizacao) OVER (ORDER BY rn) AS prev_dt,
                lag(id) OVER (ORDER BY rn) AS prev_id,
                id
            FROM ordered
        )
        SELECT count(*) FROM lagged
        WHERE prev_np IS NOT NULL AND (
            numero_processo < prev_np
            OR (numero_processo = prev_np AND data_disponibilizacao < prev_dt)
            OR (numero_processo = prev_np AND data_disponibilizacao = prev_dt AND id < prev_id)
        )
        """
    ).fetchone()[0]


def _kv_metadata(con: duckdb.DuckDBPyConnection, path: Path) -> dict[str, str]:
    rows = con.execute(
        f"SELECT key, value FROM parquet_kv_metadata('{path.as_posix()}')"
    ).fetchall()
    return {
        (k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)): (
            v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
        )
        for k, v in rows
    }


def _compression_codecs(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    rows = con.execute(
        f"SELECT DISTINCT compression FROM parquet_metadata('{path.as_posix()}')"
    ).fetchall()
    return sorted({str(r[0]) for r in rows})


def compare(old_path: Path, candidate_path: Path, old_sha256: str) -> PilotReport:
    """Compare the old file against the candidate rewrite and build a report."""
    con = duckdb.connect(":memory:")
    old_sql = f"read_parquet('{old_path.as_posix()}')"
    candidate_sql = f"read_parquet('{candidate_path.as_posix()}')"
    errors: list[str] = []

    old_count = con.execute(f"SELECT count(*) FROM {old_sql}").fetchone()[0]
    candidate_count = con.execute(f"SELECT count(*) FROM {candidate_sql}").fetchone()[0]
    row_count_matches = old_count == candidate_count
    if not row_count_matches:
        errors.append(f"row count changed: old={old_count} candidate={candidate_count}")

    old_ids = {r[0] for r in con.execute(f"SELECT id FROM {old_sql}").fetchall()}
    candidate_ids = {r[0] for r in con.execute(f"SELECT id FROM {candidate_sql}").fetchall()}
    id_set_matches = old_ids == candidate_ids
    if not id_set_matches:
        errors.append(
            f"id sets differ: only_old={len(old_ids - candidate_ids)} "
            f"only_candidate={len(candidate_ids - old_ids)}"
        )

    normalized_value_count = con.execute(
        f"""
        SELECT count(*) FROM {old_sql} o JOIN {candidate_sql} c USING (id)
        WHERE o.numero_processo IS DISTINCT FROM c.numero_processo
        """
    ).fetchone()[0]

    normalization_contract_violations = con.execute(
        f"""
        SELECT count(*) FROM {old_sql} o JOIN {candidate_sql} c USING (id)
        WHERE CASE
            WHEN o.numero_processo IS NULL THEN c.numero_processo IS NOT NULL
            WHEN length(regexp_replace(o.numero_processo, '[^0-9]', '', 'g')) = 20
                THEN c.numero_processo IS DISTINCT FROM
                     regexp_replace(o.numero_processo, '[^0-9]', '', 'g')
            ELSE c.numero_processo IS DISTINCT FROM o.numero_processo
        END
        """
    ).fetchone()[0]
    if normalization_contract_violations:
        errors.append(
            f"{normalization_contract_violations} rows violate the CNJ normalization contract"
        )

    fields_diff = con.execute(
        f"""
        SELECT count(*) FROM (
            SELECT * EXCLUDE (numero_processo) FROM {old_sql}
            EXCEPT
            SELECT * EXCLUDE (numero_processo) FROM {candidate_sql}
        )
        """
    ).fetchone()[0]
    other_fields_untouched = fields_diff == 0
    if not other_fields_untouched:
        errors.append(f"{fields_diff} rows have a non-numero_processo field change")

    candidate_footer_boundary_ties = _footer_boundary_ties(con, candidate_path)
    candidate_sort_violations = _sort_violations(con, candidate_path)
    if candidate_sort_violations:
        errors.append(
            f"{candidate_sort_violations} rows break the "
            "numero_processo/data_disponibilizacao/id physical order contract"
        )

    candidate_kv_metadata = _kv_metadata(con, candidate_path)
    kv_metadata_matches_expected = all(
        candidate_kv_metadata.get(k) == v for k, v in EXPECTED_KV_METADATA.items()
    )
    if not kv_metadata_matches_expected:
        errors.append(f"candidate KV metadata does not match expected: {candidate_kv_metadata}")

    candidate_compression_codecs = _compression_codecs(con, candidate_path)
    if candidate_compression_codecs != ["ZSTD"]:
        errors.append(f"unexpected compression codecs: {candidate_compression_codecs}")

    spot_check_digits = "".join(ch for ch in SPOT_CHECK_CNJ if ch.isdigit())
    spot_check_old_matches = con.execute(
        f"""
        SELECT count(*) FROM {old_sql}
        WHERE numero_processo = ? OR regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?
        """,
        [SPOT_CHECK_CNJ, spot_check_digits],
    ).fetchone()[0]
    spot_check_candidate_matches = con.execute(
        f"SELECT count(*) FROM {candidate_sql} WHERE numero_processo = ?",
        [spot_check_digits],
    ).fetchone()[0]
    spot_check_agrees = spot_check_old_matches == spot_check_candidate_matches
    if not spot_check_agrees:
        errors.append(
            f"spot check CNJ mismatch: old={spot_check_old_matches} "
            f"candidate={spot_check_candidate_matches}"
        )

    passed = not errors

    return PilotReport(
        item_id=ITEM_ID,
        table_name=TABLE_NAME,
        old_url=SOURCE_URL,
        old_sha256=old_sha256,
        old_row_count=old_count,
        candidate_row_count=candidate_count,
        row_count_matches=row_count_matches,
        id_set_matches=id_set_matches,
        normalized_value_count=normalized_value_count,
        normalization_contract_violations=normalization_contract_violations,
        other_fields_untouched=other_fields_untouched,
        candidate_footer_boundary_ties=candidate_footer_boundary_ties,
        candidate_sort_violations=candidate_sort_violations,
        candidate_compression_codecs=candidate_compression_codecs,
        candidate_kv_metadata=candidate_kv_metadata,
        kv_metadata_matches_expected=kv_metadata_matches_expected,
        spot_check_cnj=SPOT_CHECK_CNJ,
        spot_check_old_matches=spot_check_old_matches,
        spot_check_candidate_matches=spot_check_candidate_matches,
        spot_check_agrees=spot_check_agrees,
        passed=passed,
        errors=errors,
    )


def run(work_dir: Path) -> PilotReport:
    old_path = work_dir / "old-comunicacoes.parquet"
    log.info("downloading_old_parquet", url=SOURCE_URL, dest=str(old_path))
    old_sha256 = download_old_parquet(old_path)
    log.info("building_candidate", old_path=str(old_path))
    candidate_path = build_candidate(old_path, work_dir)
    log.info("comparing", old_path=str(old_path), candidate_path=str(candidate_path))
    return compare(old_path, candidate_path, old_sha256)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("pilot-tjro-2026-report.json"))
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory to hold the downloaded/candidate Parquet files (default: temp dir).",
    )
    args = parser.parse_args()

    work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="pilot-tjro-2026-"))
    work_dir.mkdir(parents=True, exist_ok=True)

    report = run(work_dir)
    args.output.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    log.info("report_written", path=str(args.output), passed=report.passed)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
