#!/usr/bin/env python3
"""IA practicality probe — verify consolidated Parquets on Internet Archive.

Discovers djen-* items on IA, reads Parquet metadata via DuckDB httpfs,
and checks schema/row counts against expected columns per table.

Exit 0 = all good, exit 1 = hard failures found.

Usage:
    python scripts/ia_practicality_probe.py --sample 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import httpx
import structlog


log = structlog.get_logger()

IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_DOWNLOAD_BASE = "https://archive.org/download"

MINIMAL_REQUIRED_COLUMNS: dict[str, list[str]] = {
    "comunicacoes": ["id", "tribunal", "data_disponibilizacao"],
    "textos": ["id", "texto"],
    "advogados": ["id"],
    "destinatarios": ["comunicacao_id"],
    "processos": ["numero_processo", "tribunal"],
    "classificacoes": ["outcome", "confidence"],
}


def discover_items(limit: int = 10) -> list[str]:
    """Find djen-YYYY-MM-DD items on IA via advanced search."""
    params = {
        "q": "identifier:djen-2* AND mediatype:data",
        "fl[]": "identifier",
        "rows": str(limit),
        "sort[]": "addeddate desc",
        "output": "json",
    }
    resp = httpx.get(IA_SEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])
    return [d["identifier"] for d in docs]


def list_parquets(item_id: str) -> list[str]:
    """List .parquet files in an IA item."""
    try:
        resp = httpx.get(
            f"{IA_DOWNLOAD_BASE}/{item_id}",
            params={"output": "json"},
            timeout=30,
        )
        resp.raise_for_status()
        files = resp.json().get("files", {})
        return [name for name in files if name.endswith(".parquet")]
    except httpx.HTTPError as exc:
        log.warning("item_metadata_failed", item_id=item_id, error=str(exc))
        return []


def probe_parquet(item_id: str, filename: str) -> dict:
    """Probe a single Parquet file via DuckDB httpfs."""
    url = f"{IA_DOWNLOAD_BASE}/{item_id}/{filename}"
    table_name = filename.replace(".parquet", "")
    result = {
        "table": table_name,
        "url": url,
        "status": "ok",
        "rows": 0,
        "columns": [],
        "errors": [],
        "warnings": [],
    }

    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")

        cols = con.execute(f"DESCRIBE SELECT * FROM '{url}'").fetchall()
        result["columns"] = [c[0] for c in cols]

        row_count = con.execute(f"SELECT COUNT(*) FROM '{url}'").fetchone()[0]
        result["rows"] = row_count

        if row_count == 0:
            result["errors"].append("zero rows")
            result["status"] = "fail"

        expected = MINIMAL_REQUIRED_COLUMNS.get(table_name, [])
        actual_set = set(result["columns"])
        missing = [c for c in expected if c not in actual_set]
        if missing:
            result["errors"].append(f"missing required columns: {missing}")
            result["status"] = "fail"

    except duckdb.Error as exc:
        result["errors"].append(f"DuckDB error: {exc}")
        result["status"] = "fail"
    finally:
        con.close()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="IA Practicality Probe")
    parser.add_argument("--sample", type=int, default=5, help="Number of items to probe")
    args = parser.parse_args()

    items = discover_items(limit=args.sample)
    log.info("discovered_items", count=len(items))

    report = {
        "items_probed": 0,
        "tables_checked": 0,
        "hard_failures": 0,
        "warnings": 0,
        "details": [],
    }

    for item_id in items:
        parquets = list_parquets(item_id)
        if not parquets:
            log.warning("no_parquets", item_id=item_id)
            continue

        report["items_probed"] += 1
        item_results = []

        for filename in parquets:
            result = probe_parquet(item_id, filename)
            report["tables_checked"] += 1
            if result["status"] == "fail":
                report["hard_failures"] += len(result["errors"])
                log.error(
                    "probe_failure",
                    item_id=item_id,
                    table=result["table"],
                    errors=result["errors"],
                )
            if result["warnings"]:
                report["warnings"] += len(result["warnings"])
            item_results.append(result)

        report["details"].append({"item_id": item_id, "tables": item_results})
        log.info(
            "item_probed",
            item_id=item_id,
            tables=len(parquets),
            ok=sum(1 for r in item_results if r["status"] == "ok"),
        )

    report_path = Path("/tmp/ia-probe-report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    log.info(
        "probe_complete",
        items=report["items_probed"],
        tables=report["tables_checked"],
        failures=report["hard_failures"],
    )

    if report["hard_failures"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
