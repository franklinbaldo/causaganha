#!/usr/bin/env python3
"""
Internet Archive Discovery - List and query uploaded TJRO diarios

This script provides various ways to discover and list TJRO diarios
that have been uploaded to Internet Archive.
"""

import requests
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, date
import argparse
import time


class IADiscovery:
    """Internet Archive discovery and listing tool."""

    def __init__(self):
        self.base_search_url = "https://archive.org/advancedsearch.php"
        self.base_details_url = "https://archive.org/details"
        self.logger = logging.getLogger(__name__)

    def search_tjro_diarios(
        self,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        rows: int = 1000,
    ) -> List[Dict]:
        """Search for TJRO diarios in Internet Archive."""

        # Build search query
        query_parts = [
            'creator:"Tribunal de Justiça de Rondônia"',
            'title:"Diário da Justiça TJRO"',
        ]

        if year:
            query_parts.append(f"date:[{year}-01-01 TO {year}-12-31]")
        elif start_date and end_date:
            query_parts.append(f"date:[{start_date} TO {end_date}]")

        query = " AND ".join(query_parts)

        # Search parameters
        params = {
            "q": query,
            "fl": "identifier,title,description,date,creator,downloads,item_size,publicdate,addeddate",
            "sort": "date desc",
            "rows": rows,
            "page": 1,
            "output": "json",
        }

        try:
            self.logger.info(f"Searching IA with query: {query}")
            response = requests.get(self.base_search_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            items = data.get("response", {}).get("docs", [])

            self.logger.info(f"Found {len(items)} items in Internet Archive")
            return items

        except Exception as e:
            self.logger.error(f"IA search failed: {e}")
            return []

    def get_detailed_item_info(self, identifier: str) -> Optional[Dict]:
        """Get detailed information about a specific IA item."""
        try:
            metadata_url = f"https://archive.org/metadata/{identifier}"
            response = requests.get(metadata_url, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            self.logger.error(f"Failed to get details for {identifier}: {e}")
            return None

    def list_by_identifier_pattern(self, year: Optional[int] = None) -> List[str]:
        """List diarios by checking identifier patterns directly."""
        identifiers = []

        # If year specified, generate expected identifiers for that year
        if year:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            current_date = start_date
            while current_date <= end_date:
                identifier = f"tjro-diario-{current_date.strftime('%Y-%m-%d')}"

                # Check if this identifier exists
                if self.check_identifier_exists(identifier):
                    identifiers.append(identifier)

                current_date = date.fromordinal(current_date.toordinal() + 1)

                # Small delay to be respectful
                time.sleep(0.1)

        return identifiers

    def check_identifier_exists(self, identifier: str) -> bool:
        """Check if an Internet Archive identifier exists."""
        try:
            metadata_url = f"https://archive.org/metadata/{identifier}"
            response = requests.head(metadata_url, timeout=10)
            return response.status_code == 200

        except Exception:
            return False

    def get_collection_items(self, collection: str = "opensource") -> List[Dict]:
        """Get all items from a specific collection that match our criteria."""
        query = f'collection:{collection} AND creator:"Tribunal de Justiça de Rondônia"'

        params = {
            "q": query,
            "fl": "identifier,title,date,downloads,item_size",
            "sort": "date desc",
            "rows": 10000,  # Large number to get all items
            "output": "json",
        }

        try:
            response = requests.get(self.base_search_url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()
            items = data.get("response", {}).get("docs", [])

            return items

        except Exception as e:
            self.logger.error(f"Collection search failed: {e}")
            return []

    def generate_coverage_report(self, year: Optional[int] = None) -> Dict:
        """Generate a coverage report showing what's available vs what should exist."""

        # Get what's actually in IA
        ia_items = self.search_tjro_diarios(year=year)
        ia_dates = set()

        for item in ia_items:
            try:
                item_date = item.get("date")
                if item_date:
                    # Handle different date formats
                    if "T" in item_date:
                        item_date = item_date.split("T")[0]
                    ia_dates.add(item_date)
            except Exception:
                continue

        # Load our pipeline data to see what should exist
        expected_dates = set()
        try:
            pipeline_file = "data/diarios_pipeline_ready.json"
            with open(pipeline_file, "r") as f:
                pipeline_data = json.load(f)

            for item in pipeline_data:
                item_year = item.get("year")
                if not year or item_year == year:
                    expected_dates.add(item["date"])

        except Exception as e:
            self.logger.warning(f"Could not load pipeline data: {e}")

        # Calculate coverage
        if expected_dates:
            coverage_percentage = (
                len(ia_dates & expected_dates) / len(expected_dates) * 100
            )
            missing_dates = expected_dates - ia_dates
            extra_dates = ia_dates - expected_dates
        else:
            coverage_percentage = 0
            missing_dates = set()
            extra_dates = ia_dates

        return {
            "year": year,
            "total_in_ia": len(ia_items),
            "total_expected": len(expected_dates),
            "coverage_percentage": coverage_percentage,
            "missing_count": len(missing_dates),
            "missing_dates": sorted(list(missing_dates)),
            "extra_count": len(extra_dates),
            "extra_dates": sorted(list(extra_dates)),
            "ia_dates": sorted(list(ia_dates)),
        }

    def export_ia_inventory(self, output_file: str, year: Optional[int] = None) -> None:
        """Export complete inventory of TJRO diarios in IA."""
        items = self.search_tjro_diarios(year=year)

        # Enhance with detailed info if needed
        enhanced_items = []
        for item in items[:10]:  # Limit detailed queries for demo
            detailed = self.get_detailed_item_info(item["identifier"])
            if detailed:
                item["detailed_metadata"] = detailed.get("metadata", {})
                item["files"] = detailed.get("files", [])
            enhanced_items.append(item)

        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.utcnow().isoformat(),
                    "query_year": year,
                    "total_items": len(items),
                    "items": enhanced_items if len(items) <= 10 else items,
                },
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        self.logger.info(f"Exported {len(items)} items to {output_file}")


def main():
    """CLI interface for IA discovery."""
    parser = argparse.ArgumentParser(
        description="Discover and list TJRO diarios in Internet Archive"
    )
    parser.add_argument("--year", "-y", type=int, help="Filter by specific year")
    parser.add_argument("--start-date", type=str, help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date filter (YYYY-MM-DD)")
    parser.add_argument(
        "--coverage-report",
        "-c",
        action="store_true",
        help="Generate coverage report (what's missing vs expected)",
    )
    parser.add_argument(
        "--export", "-e", type=str, help="Export inventory to JSON file"
    )
    parser.add_argument(
        "--check-identifier", type=str, help="Check if specific identifier exists"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="opensource",
        help="Search within specific collection",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    discovery = IADiscovery()

    # Check single identifier
    if args.check_identifier:
        exists = discovery.check_identifier_exists(args.check_identifier)
        print(
            f"Identifier '{args.check_identifier}': {'EXISTS' if exists else 'NOT FOUND'}"
        )
        if exists:
            details = discovery.get_detailed_item_info(args.check_identifier)
            if details:
                metadata = details.get("metadata", {})
                print(f"Title: {metadata.get('title', 'N/A')}")
                print(f"Date: {metadata.get('date', 'N/A')}")
                print(f"URL: https://archive.org/details/{args.check_identifier}")
        return 0

    # Generate coverage report
    if args.coverage_report:
        print("🔍 Generating coverage report...")
        report = discovery.generate_coverage_report(year=args.year)

        print(
            "\n📊 Coverage Report"
            + (f" for {report['year']}" if report["year"] else "")
        )
        print(f"   Items in IA: {report['total_in_ia']:,}")
        print(f"   Expected items: {report['total_expected']:,}")
        print(f"   Coverage: {report['coverage_percentage']:.1f}%")
        print(f"   Missing: {report['missing_count']:,}")
        print(f"   Extra: {report['extra_count']:,}")

        if report["missing_dates"] and len(report["missing_dates"]) <= 20:
            print("\n📅 Missing dates:")
            for date_str in report["missing_dates"][:10]:
                print(f"   - {date_str}")
            if len(report["missing_dates"]) > 10:
                print(f"   ... and {len(report['missing_dates']) - 10} more")

        return 0

    # Search and list items
    items = discovery.search_tjro_diarios(
        year=args.year, start_date=args.start_date, end_date=args.end_date
    )

    if not items:
        print("No items found in Internet Archive.")
        return 0

    # Display results
    print(f"\n📚 Found {len(items)} TJRO diarios in Internet Archive:")
    print("=" * 80)

    for i, item in enumerate(items[:20], 1):  # Show first 20
        identifier = item.get("identifier", "Unknown")
        title = item.get("title", "No title")
        date_str = item.get("date", "No date")
        downloads = item.get("downloads", 0)
        size = item.get("item_size", 0)

        print(f"{i:3d}. {identifier}")
        print(f"     Title: {title}")
        print(f"     Date: {date_str}")
        print(f"     Downloads: {downloads:,} | Size: {size:,} bytes")
        print(f"     URL: https://archive.org/details/{identifier}")
        print()

    if len(items) > 20:
        print(f"... and {len(items) - 20} more items")

    # Export if requested
    if args.export:
        discovery.export_ia_inventory(args.export, year=args.year)
        print(f"\n💾 Inventory exported to: {args.export}")

    return 0


if __name__ == "__main__":
    exit(main())
