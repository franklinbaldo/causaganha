#!/usr/bin/env python3
"""Prove the TCU Acórdãos bulk contract against one real official annual CSV.

Purpose:  #984 requires downloading at least one real annual Acórdãos CSV, running the
          #1002 parser against it in full, comparing the observed schema against the
          documented dictionary, and measuring the cost of historical expansion — before
          any TCU coverage is announced on the MCP/site surface.
Problem:  Every prior TCU slice (#1002, #1006, #1008, #1009) proved the deterministic
          transform, safe acquisition, and manifest-driven URL resolution in isolation,
          against fixtures or a single range-request header check. None of them ran the
          parser against a complete, really-downloaded official file.
Strategy: Fetch the official files manifest, resolve one year's Acórdãos URL, download it
          with acquisition.download_official_csv (atomic, evidenced), load and transform it
          with the #1002 parser, diff the observed header against the documented contract,
          measure the total historical Acórdãos size across every year in the manifest, and
          write a JSON evidence report — never the raw bulk CSV — under docs/data/.
Status:   one-off proof for #984, run manually. Not part of any CI job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from tcu_acordaos.acquisition import download_official_csv
from tcu_acordaos.catalog import parse_manifest, resolve_acordaos_url
from tcu_acordaos.coverage import total_acordaos_size_bytes, years_available
from tcu_acordaos.ingest import AcquisitionProvenance, load_csv, search_teor, transform_rows
from tcu_acordaos.schema_diff import diff_header

_MANIFEST_URL = (
    "https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/jurisprudencia-arquivos.csv"
)


def build_report(
    *,
    year: str,
    source_url: str,
    final_url: str,
    acquired_at: str,
    size_bytes: int,
    sha256: str,
    observed_header: list[str],
    record_count: int,
    total_historical_bytes: int,
    years: list[str],
    sample_query: str,
    sample_hits: int,
) -> dict:
    """Assemble the JSON-serializable evidence report. Pure — no I/O."""
    diff = diff_header(observed_header)
    return {
        "year": year,
        "source_url": source_url,
        "final_url": final_url,
        "acquired_at": acquired_at,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "record_count": record_count,
        "observed_header": observed_header,
        "schema": {
            "missing_required_columns": list(diff.missing),
            "extra_observed_columns": list(diff.extra),
            "is_compatible": diff.is_compatible,
        },
        "historical_expansion": {
            "years_available": years,
            "year_count": len(years),
            "total_size_bytes": total_historical_bytes,
        },
        "sample_teor_query": {"query": sample_query, "hit_count": sample_hits},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year", default="1992", help="Official Acórdãos year to prove against (default: 1992)"
    )
    parser.add_argument(
        "--query", default="tomada de contas", help="Sample TEOR query to prove provenance"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/data/tcu-acordaos-bulk-proof.json"),
        help="Where to write the JSON evidence report",
    )
    parser.add_argument(
        "--csv-scratch",
        type=Path,
        default=Path("/tmp/tcu-acordaos-bulk.csv"),
        help="Scratch path for the downloaded CSV (never committed)",
    )
    args = parser.parse_args(argv)

    with urlopen(_MANIFEST_URL) as response:  # noqa: S310 - fixed official TCU host
        manifest_text = response.read().decode("utf-8-sig")
    entries = parse_manifest(manifest_text)
    url = resolve_acordaos_url(entries, year=args.year)

    evidence = download_official_csv(url, args.csv_scratch)
    rows = load_csv(args.csv_scratch)
    if not rows:
        msg = f"downloaded {args.year} Acórdãos CSV has no data rows"
        raise ValueError(msg)

    provenance = AcquisitionProvenance(
        source_url=evidence.source_url,
        acquired_at=evidence.acquired_at,
        sha256=evidence.sha256,
    )
    records = transform_rows(rows, provenance=provenance)
    hits = search_teor(records, args.query)

    report = build_report(
        year=args.year,
        source_url=evidence.source_url,
        final_url=evidence.final_url,
        acquired_at=evidence.acquired_at,
        size_bytes=evidence.size_bytes,
        sha256=evidence.sha256,
        observed_header=list(rows[0].keys()),
        record_count=len(records),
        total_historical_bytes=total_acordaos_size_bytes(entries),
        years=years_available(entries),
        sample_query=args.query,
        sample_hits=len(hits),
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
