#!/usr/bin/env python3
"""Investigate whether a candidate field can canonically identify pre-2017 TCU Acórdãos.

Purpose:  #1012 found that the official ``KEY`` column — the unique identifier
          ``tcu_acordaos.ingest`` requires — appears in the bulk Acórdãos files for 2017+
          but not for 1992-2016. Before that historical window can be exposed on any
          MCP/site surface, #1012 requires evidence (not invention) that some other field,
          or composite of fields, is unique and stable across the real corpus.
Problem:  #1027 built the instrument (``tcu_acordaos.identity_candidates``) this
          investigation needs but deliberately did not run it against real data — that
          needed the actual official bulk files pulled year by year, a separate effort.
Strategy: Fetch the official files manifest (same one #1008/#984 use), record the observed
          header for every year 1992-2016 via a cheap byte-range request (proves ``KEY`` is
          genuinely absent everywhere in the window, not just in the years sampled so far),
          then fully download three representative years — the start (1992), a middle year
          (2004), and the end (2016, required by #1012's acceptance criteria) — and run
          ``analyze_key_candidates`` against each. The decision (accept a candidate, or
          declare the window ineligible) is derived only from that evidence, never assumed.
          Writes one JSON evidence report — never the raw bulk CSVs — under docs/data/.
Status:   one-off proof for #1012, run manually. Not part of any CI job.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from tcu_acordaos.acquisition import download_official_csv, validate_official_url
from tcu_acordaos.catalog import parse_manifest, resolve_acordaos_url
from tcu_acordaos.identity_candidates import analyze_key_candidates, load_csv_raw

_MANIFEST_URL = (
    "https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/jurisprudencia-arquivos.csv"
)

FIRST_YEAR = 1992
LAST_YEAR = 2016

# Start, a middle year, and the end — #1012 requires "at least one complete file each of
# start, middle and end of the period, including 2016". 2004 sits in the middle of the
# window at a moderate file size (~114 MB per the official manifest, sampled 2026-09-03),
# well short of the ~330 MB later years in this window carry.
FULL_DOWNLOAD_YEARS = ("1992", "2004", "2016")

# Ordered simplest-first: a single field is preferred identity if the evidence supports it;
# composites are only worth adopting if no simpler candidate proves stable. Reflects #1012's
# named risks directly: NUMACORDAO repeats across colegiados/types, PROC can span more than
# one acórdão over time — hence the composites that add ANOACORDAO/COLEGIADO to disambiguate.
CANDIDATE_FIELDS: tuple[tuple[str, ...], ...] = (
    ("NUMACORDAO",),
    ("PROC",),
    ("NUMACORDAO", "ANOACORDAO"),
    ("PROC", "ANOACORDAO"),
    ("NUMACORDAO", "ANOACORDAO", "COLEGIADO"),
    ("PROC", "ANOACORDAO", "COLEGIADO"),
)


def candidate_key_name(fields: tuple[str, ...]) -> str:
    """Stable string key for a candidate field/composite, used as a report/dict key."""
    return "+".join(fields)


def parse_header_line(raw_text: str) -> list[str]:
    """Parse the header row out of a byte-range prefix of an official TCU bulk CSV."""
    first_line = raw_text.splitlines()[0]
    return next(csv.reader([first_line], delimiter="|", quotechar='"'))


def fetch_header_via_range(url: str, *, range_bytes: int = 4096) -> list[str]:
    """Fetch just enough bytes to read the header row, via an HTTP Range request.

    Confirmed against the real TCU CDN (2026-09-03): it answers with 206 Partial Content,
    so a full download is unnecessary just to prove which columns a given year's file has.
    """
    validate_official_url(url)
    request = Request(url, headers={"Range": f"bytes=0-{range_bytes - 1}"})  # noqa: S310
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed official TCU host
        raw = response.read().decode("utf-8-sig", errors="replace")
    return parse_header_line(raw)


def _decide_candidate(candidate_reports: dict[str, dict[str, dict]], full_years: list[str]) -> dict:
    for fields in CANDIDATE_FIELDS:
        name = candidate_key_name(fields)
        stable_everywhere = all(
            candidate_reports.get(year, {}).get(name, {}).get("is_stable") is True
            for year in full_years
        )
        if stable_everywhere:
            return {
                "status": "accepted",
                "accepted_candidate": name,
                "rationale": (
                    f"{name} has zero null rows and zero collisions in every fully-tested "
                    f"year ({', '.join(full_years)})"
                ),
            }
    return {
        "status": "ineligible",
        "accepted_candidate": None,
        "rationale": (
            "no candidate field/composite proved stable (zero null rows, zero collisions) "
            f"in every fully-tested year ({', '.join(full_years)}); 1992-2016 stays "
            "ineligible for canonical identity until a better candidate or an official KEY "
            "backfill exists — see #1012"
        ),
    }


def build_identity_report(
    *,
    header_evidence: dict[str, list[str]],
    full_year_evidence: dict[str, dict],
    candidate_reports: dict[str, dict[str, dict]],
) -> dict:
    """Assemble the JSON-serializable #1012 evidence report and its identity decision.

    Pure — no I/O. ``full_year_evidence`` must include "2016": #1012 explicitly requires the
    end of the window among the fully-validated years, not just start/middle.
    """
    if "2016" not in full_year_evidence:
        msg = "full_year_evidence must include 2016 (the end of the 1992-2016 window)"
        raise ValueError(msg)

    full_years = sorted(full_year_evidence)
    return {
        "window": {"first_year": FIRST_YEAR, "last_year": LAST_YEAR},
        "header_evidence": dict(sorted(header_evidence.items())),
        "full_year_evidence": full_year_evidence,
        "candidate_reports": candidate_reports,
        "decision": _decide_candidate(candidate_reports, full_years),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/data/tcu-acordaos-identity-1992-2016.json"),
        help="Where to write the JSON evidence report",
    )
    parser.add_argument(
        "--csv-scratch-dir",
        type=Path,
        default=Path("/tmp/tcu-acordaos-identity"),
        help="Scratch directory for downloaded CSVs (never committed)",
    )
    args = parser.parse_args(argv)

    with urlopen(_MANIFEST_URL, timeout=30) as response:  # noqa: S310 - fixed official TCU host
        manifest_text = response.read().decode("utf-8-sig")
    entries = parse_manifest(manifest_text)

    header_evidence: dict[str, list[str]] = {}
    for year in (str(y) for y in range(FIRST_YEAR, LAST_YEAR + 1)):
        url = resolve_acordaos_url(entries, year=year)
        header_evidence[year] = fetch_header_via_range(url)

    args.csv_scratch_dir.mkdir(parents=True, exist_ok=True)
    full_year_evidence: dict[str, dict] = {}
    candidate_reports: dict[str, dict[str, dict]] = {}
    for year in FULL_DOWNLOAD_YEARS:
        url = resolve_acordaos_url(entries, year=year)
        destination = args.csv_scratch_dir / f"acordao-completo-{year}.csv"
        evidence = download_official_csv(url, destination)
        rows = load_csv_raw(destination)
        reports = analyze_key_candidates(rows, list(CANDIDATE_FIELDS))
        candidate_reports[year] = {
            candidate_key_name(fields): {
                "total_rows": report.total_rows,
                "null_rows": report.null_rows,
                "unique_values": report.unique_values,
                "colliding_values": report.colliding_values,
                "max_collision_size": report.max_collision_size,
                "is_stable": report.is_stable,
            }
            for fields, report in reports.items()
        }
        full_year_evidence[year] = {
            "source_url": evidence.source_url,
            "final_url": evidence.final_url,
            "acquired_at": evidence.acquired_at,
            "size_bytes": evidence.size_bytes,
            "sha256": evidence.sha256,
            "record_count": len(rows),
        }
        destination.unlink(missing_ok=True)  # evidence is recorded; never commit raw bulk CSVs

    report = build_identity_report(
        header_evidence=header_evidence,
        full_year_evidence=full_year_evidence,
        candidate_reports=candidate_reports,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["decision"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
