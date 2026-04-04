"""Generate a snapshot of all CausaGanha items on Internet Archive.

Queries IA metadata for each tribunal x year item, extracts ZIP file
lists, and writes a single ia-snapshot.json consumed by the dashboard.

Usage:
    python scripts/generate_ia_snapshot.py [--output path] [--years 2024,2025,2026]
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx


# Tribunal list — mirrors src/djen_backup/tribunais.py
TRIBUNAIS = [
    "CJF",
    "PJeCor",
    "SEEU",
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
    "STF",
    "STJ",
    "TST",
    "TSE",
    "STM",
    "CNJ",
    "TJAC",
    "TJAL",
    "TJAM",
    "TJAP",
    "TJBA",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMG",
    "TJMS",
    "TJMT",
    "TJPA",
    "TJPB",
    "TJPE",
    "TJPI",
    "TJPR",
    "TJRJ",
    "TJRN",
    "TJRO",
    "TJRR",
    "TJRS",
    "TJSC",
    "TJSE",
    "TJSP",
    "TJTO",
    "TJMMG",
    "TJMRS",
    "TJMSP",
    "TRT1",
    "TRT2",
    "TRT3",
    "TRT4",
    "TRT5",
    "TRT6",
    "TRT7",
    "TRT8",
    "TRT9",
    "TRT10",
    "TRT11",
    "TRT12",
    "TRT13",
    "TRT14",
    "TRT15",
    "TRT16",
    "TRT17",
    "TRT18",
    "TRT19",
    "TRT20",
    "TRT21",
    "TRT22",
    "TRT23",
    "TRT24",
    "TRE-AC",
    "TRE-AL",
    "TRE-AM",
    "TRE-AP",
    "TRE-BA",
    "TRE-CE",
    "TRE-DF",
    "TRE-ES",
    "TRE-GO",
    "TRE-MA",
    "TRE-MG",
    "TRE-MS",
    "TRE-MT",
    "TRE-PA",
    "TRE-PB",
    "TRE-PE",
    "TRE-PI",
    "TRE-PR",
    "TRE-RJ",
    "TRE-RN",
    "TRE-RO",
    "TRE-RR",
    "TRE-RS",
    "TRE-SC",
    "TRE-SE",
    "TRE-SP",
    "TRE-TO",
]

IA_METADATA_URL = "https://archive.org/metadata/{item_id}"
CONCURRENCY = 10
DATE_RE = re.compile(r"djen-(\d{4}-\d{2}-\d{2})-.*\.zip$", re.IGNORECASE)


def get_item_id(tribunal: str, year: int) -> str:
    return f"djen-{tribunal.lower()}-{year}"


def extract_date_from_zip(filename: str) -> str | None:
    """Extract YYYY-MM-DD from a ZIP filename like djen-2026-01-15-TJSP.zip."""
    m = DATE_RE.match(filename)
    return m.group(1) if m else None


async def fetch_item(client: httpx.AsyncClient, item_id: str) -> dict | None:
    """Fetch metadata for a single IA item. Returns None on 404/error."""
    url = IA_METADATA_URL.format(item_id=item_id)
    try:
        resp = await client.get(url, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None


async def process_item(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    tribunal: str,
    year: int,
) -> dict | None:
    """Fetch and parse one tribunal x year item."""
    item_id = get_item_id(tribunal, year)
    async with sem:
        data = await fetch_item(client, item_id)

    if data is None:
        return None

    files = data.get("files", [])
    dates = []
    total_size = 0
    file_details = {}
    parquet_files = []

    for f in files:
        name = f.get("name", "")
        date_str = extract_date_from_zip(name)
        if date_str:
            dates.append(date_str)
            size = 0
            with contextlib.suppress(ValueError, TypeError):
                size = int(f.get("size", 0))
                total_size += size
            file_details[date_str] = {
                "size": size,
                "md5": f.get("md5"),
                "addeddate": f.get("addeddate") or f.get("mtime"),
            }
        elif name.endswith(".parquet"):
            pq_size = 0
            with contextlib.suppress(ValueError, TypeError):
                pq_size = int(f.get("size", 0))
            parquet_files.append(
                {
                    "name": name,
                    "size": pq_size,
                }
            )

    if not dates:
        return None

    # Extract item-level metadata
    item_created = None
    item_downloads = None
    metadata = data.get("metadata", {})
    item_created = metadata.get("addeddate")
    with contextlib.suppress(ValueError, TypeError):
        item_downloads = int(metadata.get("downloads", 0))

    dates.sort()
    return {
        "tribunal": tribunal,
        "year": year,
        "zip_count": len(dates),
        "total_size_bytes": total_size,
        "dates": dates,
        "latest_date": dates[-1],
        "earliest_date": dates[0],
        "file_details": file_details,
        "parquet_files": parquet_files,
        "item_created": item_created,
        "downloads": item_downloads,
    }


async def generate_snapshot(years: list[int]) -> dict:
    """Generate full snapshot across all tribunals and years."""
    sem = asyncio.Semaphore(CONCURRENCY)
    items = {}
    tasks = []

    async with httpx.AsyncClient() as client:
        for tribunal in TRIBUNAIS:
            for year in years:
                tasks.append(process_item(client, sem, tribunal, year))

        results = await asyncio.gather(*tasks)

    for result in results:
        if result is not None:
            item_id = get_item_id(result["tribunal"], result["year"])
            items[item_id] = result

    # Compute summary
    total_zips = sum(item["zip_count"] for item in items.values())
    total_size = sum(item["total_size_bytes"] for item in items.values())
    total_parquets = sum(len(item.get("parquet_files", [])) for item in items.values())
    total_parquet_size = sum(
        pq["size"] for item in items.values() for pq in item.get("parquet_files", [])
    )
    tribunals_with_data = len({item["tribunal"] for item in items.values()})
    consolidated_items = sum(1 for item in items.values() if item.get("parquet_files"))
    all_dates = [d for item in items.values() for d in item["dates"]]
    latest_date = max(all_dates) if all_dates else None

    # Per-year summary
    by_year = {}
    for year in years:
        year_items = [v for v in items.values() if v["year"] == year]
        year_zips = sum(i["zip_count"] for i in year_items)
        year_tribunals = len(year_items)
        by_year[str(year)] = {
            "zip_count": year_zips,
            "tribunals_with_data": year_tribunals,
            "tribunals_total": len(TRIBUNAIS),
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "years": years,
        "items": items,
        "summary": {
            "total_items": len(items),
            "total_zips": total_zips,
            "total_size_gb": round(total_size / (1024**3), 2),
            "tribunals_with_data": tribunals_with_data,
            "tribunals_total": len(TRIBUNAIS),
            "latest_collection_date": latest_date,
            "total_parquets": total_parquets,
            "total_parquet_size_gb": round(total_parquet_size / (1024**3), 2),
            "consolidated_items": consolidated_items,
        },
        "by_year": by_year,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate IA snapshot for CausaGanha monitor")
    current_year = datetime.now(tz=UTC).year
    parser.add_argument(
        "--years",
        default=",".join(str(y) for y in range(current_year - 2, current_year + 1)),
        help="Comma-separated years to scan (default: last 3 years)",
    )
    parser.add_argument(
        "--output",
        default="dashboard/public/ia-snapshot.json",
        help="Output path for snapshot JSON",
    )
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]
    print(
        f"Scanning {len(TRIBUNAIS)} tribunals x {len(years)} years = {len(TRIBUNAIS) * len(years)} items..."
    )

    snapshot = asyncio.run(generate_snapshot(years))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))

    s = snapshot["summary"]
    print(f"Done: {s['total_items']} items, {s['total_zips']} zips, {s['total_size_gb']} GB")
    print(f"Tribunals with data: {s['tribunals_with_data']}/{s['tribunals_total']}")
    print(f"Latest collection: {s['latest_collection_date']}")
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
