#!/usr/bin/env python3
"""
Diario Processor - Convert TJRO diario list to full PDF URLs for async pipeline

This script processes the todos_diarios_tjro.json file and converts it into
a structured list of PDF URLs ready for download and Internet Archive submission.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import date
import argparse


# TJRO base URL for constructing full PDF URLs
TJRO_BASE_URL = "https://www.tjro.jus.br"

logger = logging.getLogger(__name__)


def load_diarios_list(json_file_path: Path) -> List[Dict]:
    """Load the diarios list from JSON file."""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} diario entries from {json_file_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load {json_file_path}: {e}")
        return []


def convert_to_full_urls(diarios: List[Dict]) -> List[Dict]:
    """Convert relative URLs to full PDF URLs with metadata."""
    full_urls = []

    for diario in diarios:
        try:
            # Extract metadata
            year = diario.get("year")
            month = diario.get("month")
            day = diario.get("day")
            number = diario.get("number")
            relative_path = diario.get("relativePath")
            relative_url = diario.get("url")
            sufix = diario.get("sufix", "")  # Some entries have suffixes like "SUP"

            # Construct full URL
            full_url = f"{TJRO_BASE_URL}{relative_url}"

            # Create date object for sorting and validation
            try:
                diario_date = date(int(year), int(month), int(day))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid date in entry: {diario} - {e}")
                continue

            # Create standardized filename for our system
            standard_filename = f"dj_{year}{month.zfill(2)}{day.zfill(2)}.pdf"
            if sufix:
                standard_filename = (
                    f"dj_{year}{month.zfill(2)}{day.zfill(2)}_{sufix}.pdf"
                )

            # Create entry for async pipeline
            entry = {
                "original_filename": relative_path,
                "standard_filename": standard_filename,
                "full_url": full_url,
                "date": diario_date.isoformat(),
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "number": int(number),
                "sufix": sufix,
                "ia_identifier": f"tjro-diario-{year}-{month.zfill(2)}-{day.zfill(2)}"
                + (f"-{sufix.lower()}" if sufix else ""),
                "metadata": {
                    "title": f"Diário da Justiça TJRO - {day}/{month}/{year}"
                    + (f" ({sufix})" if sufix else ""),
                    "description": f"Diário da Justiça do Tribunal de Justiça de Rondônia - Edição {number} de {day}/{month}/{year}",
                    "creator": "Tribunal de Justiça de Rondônia",
                    "subject": "judicial; legal; tribunal; rondonia; diario",
                    "date": diario_date.isoformat(),
                    "language": "por",
                    "collection": "opensource",
                    "mediatype": "texts",
                },
            }

            full_urls.append(entry)

        except Exception as e:
            logger.error(f"Error processing diario entry {diario}: {e}")
            continue

    # Sort by date (newest first)
    full_urls.sort(key=lambda x: x["date"], reverse=True)

    logger.info(f"Converted {len(full_urls)} entries to full URLs")
    return full_urls


def filter_by_date_range(
    diarios: List[Dict],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict]:
    """Filter diarios by date range."""
    if not start_date and not end_date:
        return diarios

    filtered = []
    for diario in diarios:
        diario_date = date.fromisoformat(diario["date"])

        include = True
        if start_date:
            if diario_date < date.fromisoformat(start_date):
                include = False
        if end_date:
            if diario_date > date.fromisoformat(end_date):
                include = False

        if include:
            filtered.append(diario)

    logger.info(f"Filtered to {len(filtered)} entries in date range")
    return filtered


def filter_by_year(diarios: List[Dict], years: List[int]) -> List[Dict]:
    """Filter diarios by specific years."""
    if not years:
        return diarios

    filtered = [d for d in diarios if d["year"] in years]
    logger.info(f"Filtered to {len(filtered)} entries for years {years}")
    return filtered


def save_pipeline_ready_list(
    diarios: List[Dict], output_file: Path, format_type: str = "json"
) -> None:
    """Save the pipeline-ready list in specified format."""
    try:
        if format_type == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(diarios, f, indent=2, ensure_ascii=False, default=str)
        elif format_type == "urls_only":
            with open(output_file, "w", encoding="utf-8") as f:
                for diario in diarios:
                    f.write(f"{diario['full_url']}\n")
        elif format_type == "csv":
            import csv

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                if diarios:
                    writer = csv.DictWriter(f, fieldnames=diarios[0].keys())
                    writer.writeheader()
                    for diario in diarios:
                        # Flatten metadata for CSV
                        row = {k: v for k, v in diario.items() if k != "metadata"}
                        for meta_key, meta_val in diario["metadata"].items():
                            row[f"metadata_{meta_key}"] = meta_val
                        writer.writerow(row)

        logger.info(
            f"Saved {len(diarios)} entries to {output_file} in {format_type} format"
        )
    except Exception as e:
        logger.error(f"Failed to save to {output_file}: {e}")


def get_statistics(diarios: List[Dict]) -> Dict:
    """Get statistics about the diarios collection."""
    if not diarios:
        return {}

    years = [d["year"] for d in diarios]
    year_counts = {}
    for year in years:
        year_counts[year] = year_counts.get(year, 0) + 1

    dates = [date.fromisoformat(d["date"]) for d in diarios]

    stats = {
        "total_count": len(diarios),
        "date_range": {
            "earliest": min(dates).isoformat(),
            "latest": max(dates).isoformat(),
        },
        "years_covered": sorted(list(set(years))),
        "entries_per_year": year_counts,
        "total_size_estimate_mb": len(diarios) * 5,  # Rough estimate: 5MB per PDF
        "has_supplements": len([d for d in diarios if d.get("sufix")]),
    }

    return stats


def main():
    """Main CLI interface for diario processing."""
    parser = argparse.ArgumentParser(
        description="Convert TJRO diarios list to pipeline-ready URLs"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/todos_diarios_tjro.json"),
        help="Input JSON file with diarios list",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/diarios_pipeline_ready.json"),
        help="Output file for pipeline-ready list",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "urls_only", "csv"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        help="Filter by specific years (e.g., --years 2024 2025)",
    )
    parser.add_argument("--start-date", type=str, help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date filter (YYYY-MM-DD)")
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, do not create output file",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Load the diarios list
    diarios_raw = load_diarios_list(args.input)
    if not diarios_raw:
        logger.error("No diarios loaded, exiting")
        return 1

    # Convert to full URLs
    diarios = convert_to_full_urls(diarios_raw)

    # Apply filters
    if args.years:
        diarios = filter_by_year(diarios, args.years)

    if args.start_date or args.end_date:
        diarios = filter_by_date_range(diarios, args.start_date, args.end_date)

    # Show statistics
    stats = get_statistics(diarios)
    print("\n📊 TJRO Diarios Statistics:")
    print(f"   Total entries: {stats['total_count']:,}")
    print(
        f"   Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}"
    )
    print(f"   Years covered: {stats['years_covered']}")
    print(f"   Entries with supplements: {stats['has_supplements']}")
    print(f"   Estimated total size: ~{stats['total_size_estimate_mb']:,} MB")
    print("\n📅 Entries per year:")
    for year, count in sorted(stats["entries_per_year"].items()):
        print(f"   {year}: {count:,} entries")

    if args.stats_only:
        return 0

    # Save pipeline-ready list
    save_pipeline_ready_list(diarios, args.output, args.format)

    print(f"\n✅ Pipeline-ready list saved to: {args.output}")
    print(f"   Format: {args.format}")
    print(f"   Entries: {len(diarios):,}")

    if args.format == "json":
        print("\n🚀 Ready for async pipeline processing!")
        print("   Each entry includes:")
        print("   - Full PDF URL")
        print("   - Internet Archive identifier")
        print("   - Complete metadata for IA upload")
        print("   - Standardized filename for local storage")

    return 0


if __name__ == "__main__":
    exit(main())
