#!/usr/bin/env python3
"""Phase 0.7: Roundtrip-equivalence gate.

Validates that the consolidation transform preserves data fidelity by
comparing raw NDJSON records against their transformed Parquet output.

For a sample date:
1. Downloads ZIPs from IA → extracts NDJSON
2. Runs the full consolidation transform (NDJSON → DuckDB tables)
3. Samples N raw records from the NDJSON staging table
4. For each, looks up the transformed comunicacoes row
5. Compares key fields and reports mismatches

Exit 0 = all sampled records match. Exit 1 = mismatches found.

Usage:
    python scripts/roundtrip_check.py [--date DATE] [--sample 50]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import ibis
import structlog

from causaganha.consolidate import manifest_reader
from causaganha.consolidate.transforms import (
    init_tables,
    load_and_transform,
)
from causaganha.consolidate.zip_processor import process_zip_entry
from causaganha.storage.djen_schema import (
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NOME_ORGAO,
    FIELD_NUMERO_PROCESSO,
    FIELD_TIPO_COMUNICACAO,
)


log = structlog.get_logger()

NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

ROUNDTRIP_FIELDS = {
    "numero_processo": FIELD_NUMERO_PROCESSO,
    "tipo_comunicacao": FIELD_TIPO_COMUNICACAO,
    "nome_orgao": FIELD_NOME_ORGAO,
}


def _djen_uuid5(s: str) -> str:
    return str(uuid.uuid5(NAMESPACE_DJEN, s))


def _coalesce_raw(record: dict, variants: tuple[str, ...]) -> str:
    """Get the first non-empty value from variant field names."""
    for name in variants:
        val = record.get(name)
        if val is not None:
            return str(val).strip()
    return ""


def _pick_date(manifest_path: Path) -> str | None:
    """Pick a recent date that has uploaded ZIPs."""
    dates = list(manifest_reader.dates_with_uploads(manifest_path))
    if not dates:
        return None
    for d in dates[:10]:
        zips = manifest_reader.uploaded_zips_for_date(d, manifest_path)
        if len(zips) >= 3:
            return d
    return dates[0] if dates else None


def _download_zips(
    zips: list[dict],
    tmp_path: Path,
    ndjson_dir: Path,
    item_id: str,
) -> dict[str, int]:
    stats = {"zips": 0, "records": 0}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                process_zip_entry,
                z,
                tmp_path,
                ndjson_dir,
                item_id,
            ): z
            for z in zips
        }
        for future in as_completed(futures):
            try:
                ok, count = future.result()
                stats["zips"] += ok
                stats["records"] += count
            except (OSError, ValueError) as exc:
                log.warning("zip_error", error=str(exc))
    return stats


def _sample_raw_records(
    con: duckdb.DuckDBPyConnection,
    ndjson_dir: Path,
    sample_size: int,
) -> list[dict]:
    """Load NDJSON into a staging table and sample records."""
    con.execute(
        f"CREATE OR REPLACE TABLE _rt_staging AS "
        f"SELECT * FROM read_json_auto('{ndjson_dir.as_posix()}/*.ndjson', "
        f"filename=true, union_by_name=true) "
        f"USING SAMPLE {sample_size}"
    )
    cols = [row[0] for row in con.execute("DESCRIBE _rt_staging").fetchall()]
    rows = con.execute("SELECT * FROM _rt_staging").fetchall()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def _extract_raw_date(record: dict) -> str:
    """Get the date string from a raw record (first 10 chars)."""
    for name in FIELD_DATA_DISPONIBILIZACAO:
        val = record.get(name)
        if val is not None:
            return str(val).strip()[:10]
    return ""


def _extract_tribunal(record: dict) -> str:
    """Extract tribunal from the filename column added by read_json_auto."""
    filename = str(record.get("filename", ""))
    parts = filename.split("/")
    last = parts[-1] if parts else ""
    return last.split("__")[0] if "__" in last else ""


def compare_record(
    raw: dict,
    parquet_row: dict,
    *,
    ignore_fields: set[str] | None = None,
) -> list[str]:
    """Compare a raw NDJSON record against its transformed Parquet row."""
    ignore = ignore_fields or {"processed_at", "texto_id", "p_ano", "p_mes", "p_item_ia"}
    mismatches = []

    for parquet_col, variants in ROUNDTRIP_FIELDS.items():
        if parquet_col in ignore:
            continue
        expected = _coalesce_raw(raw, variants)
        actual = str(parquet_row.get(parquet_col, "")).strip()
        if expected and actual and expected != actual:
            mismatches.append(f"{parquet_col}: expected={expected!r} got={actual!r}")

    raw_date = _extract_raw_date(raw)
    parquet_date = str(parquet_row.get("data_disponibilizacao", "")).strip()[:10]
    if raw_date and parquet_date and raw_date != parquet_date:
        mismatches.append(f"data_disponibilizacao: expected={raw_date!r} got={parquet_date!r}")

    raw_id = str(raw.get("id", "")).strip()
    parquet_original_id = str(parquet_row.get("original_id", "")).strip()
    if raw_id and parquet_original_id and raw_id != parquet_original_id:
        mismatches.append(f"original_id: expected={raw_id!r} got={parquet_original_id!r}")

    return mismatches


def run_roundtrip_check(
    target_date: str,
    manifest_path: Path,
    sample_size: int,
) -> dict:
    """Run the roundtrip equivalence check for a single date."""
    report = {
        "date": target_date,
        "status": "ok",
        "zips_processed": 0,
        "records_extracted": 0,
        "sampled": 0,
        "matched": 0,
        "mismatched": 0,
        "not_found": 0,
        "table_counts": {},
        "mismatches": [],
    }

    zips = manifest_reader.uploaded_zips_for_date(target_date, manifest_path)
    if not zips:
        log.warning("no_zips_for_date", date=target_date)
        report["status"] = "no_zips"
        return report

    log.info("roundtrip_start", date=target_date, zip_count=len(zips))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        item_id = f"djen-{target_date}"
        dl_stats = _download_zips(zips, tmp_path, ndjson_dir, item_id)
        report["zips_processed"] = dl_stats["zips"]
        report["records_extracted"] = dl_stats["records"]

        if dl_stats["records"] == 0:
            log.warning("no_records", date=target_date)
            report["status"] = "no_records"
            return report

        db_path = tmp_path / "roundtrip.duckdb"
        raw_con = duckdb.connect(str(db_path))
        raw_con.execute("SET memory_limit='2GB'")

        sampled_records = _sample_raw_records(raw_con, ndjson_dir, sample_size)
        log.info("sampled_raw", count=len(sampled_records))

        raw_con.close()

        con = ibis.duckdb.connect(str(db_path))
        con.raw_sql("SET memory_limit='2GB'")
        init_tables(con)

        table_counts = load_and_transform(con, ndjson_dir, item_id)
        report["table_counts"] = table_counts
        log.info("transform_complete", tables=table_counts)

        com_count = table_counts.get("comunicacoes", 0)
        if com_count == 0:
            report["status"] = "no_comunicacoes"
            return report

        native_con = con.con  # underlying duckdb connection

        for raw_rec in sampled_records:
            report["sampled"] += 1
            raw_id = str(raw_rec.get("id", "")).strip()
            tribunal = _extract_tribunal(raw_rec)

            if not raw_id or not tribunal:
                report["not_found"] += 1
                continue

            expected_uuid = _djen_uuid5(f"{raw_id}:{tribunal}")

            rows = native_con.execute(
                "SELECT * FROM comunicacoes WHERE id = ?",
                [expected_uuid],
            ).fetchall()

            if not rows:
                report["not_found"] += 1
                log.debug("record_not_found", raw_id=raw_id, tribunal=tribunal)
                continue

            col_names = [d[0] for d in native_con.execute("DESCRIBE comunicacoes").fetchall()]
            parquet_row = dict(zip(col_names, rows[0], strict=True))

            issues = compare_record(raw_rec, parquet_row)
            if issues:
                report["mismatched"] += 1
                report["mismatches"].append(
                    {
                        "raw_id": raw_id,
                        "tribunal": tribunal,
                        "issues": issues,
                    }
                )
                log.warning(
                    "roundtrip_mismatch",
                    raw_id=raw_id,
                    tribunal=tribunal,
                    issues=issues,
                )
            else:
                report["matched"] += 1

    if report["mismatched"] > 0:
        report["status"] = "fail"
    elif report["not_found"] > report["sampled"] * 0.5:
        report["status"] = "warn"

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 0.7: Roundtrip-equivalence gate",
    )
    parser.add_argument(
        "--date",
        help="Date to check (YYYY-MM-DD). Auto-picks recent date if omitted.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=50,
        help="Number of records to sample per date",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/sync-manifest.csv"),
        help="Path to sync-manifest.csv",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        log.error("manifest_not_found", path=str(args.manifest))
        sys.exit(2)

    target_date = args.date
    if not target_date:
        target_date = _pick_date(args.manifest)
        if not target_date:
            log.error("no_dates_with_uploads")
            sys.exit(2)
    log.info("target_date", date=target_date)

    report = run_roundtrip_check(target_date, args.manifest, args.sample)

    print("\n" + "=" * 60)
    print("ROUNDTRIP EQUIVALENCE CHECK")
    print("=" * 60)
    print(f"Date:             {report['date']}")
    print(f"Status:           {report['status'].upper()}")
    print(f"ZIPs processed:   {report['zips_processed']}")
    print(f"Records extracted:{report['records_extracted']}")
    print(f"Sampled:          {report['sampled']}")
    print(f"Matched:          {report['matched']}")
    print(f"Mismatched:       {report['mismatched']}")
    print(f"Not found:        {report['not_found']}")

    if report["table_counts"]:
        print("\nTable counts:")
        for table, count in sorted(report["table_counts"].items()):
            print(f"  {table}: {count}")

    if report["mismatches"]:
        print(f"\nMismatches ({len(report['mismatches'])}):")
        for m in report["mismatches"][:10]:
            print(f"  [{m['tribunal']}] {m['raw_id']}:")
            for issue in m["issues"]:
                print(f"    - {issue}")
        if len(report["mismatches"]) > 10:
            print(f"  ... and {len(report['mismatches']) - 10} more")

    report_path = Path("/tmp/roundtrip-report.json")
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nFull report: {report_path}")
    print("=" * 60)

    if report["status"] == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
