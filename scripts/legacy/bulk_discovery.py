#!/usr/bin/env python3
"""
Bulk PDF Discovery Script - Populate queue with all available PDFs from TJRO (1970-2025)

This script discovers all available PDFs from the TJRO website and populates
the discovery queue for processing through the pipeline.

Usage:
    python scripts/bulk_discovery.py --start-year 1970 --end-year 2025
    python scripts/bulk_discovery.py --year 2024  # Single year
    python scripts/bulk_discovery.py --latest     # Latest only
"""

import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Set
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import CausaGanhaDB
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TJROPDFDiscovery:
    """Discover PDFs from TJRO website and populate database queue."""

    def __init__(self, db: CausaGanhaDB):
        self.db = db
        self.session = self._setup_session()
        self.base_url = "https://www.tjro.jus.br/diario_oficial"
        self.discovered_urls: Set[str] = set()

    def _setup_session(self) -> requests.Session:
        """Setup requests session with retry strategy."""
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers to appear more like a browser
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        return session

    def discover_year(self, year: int) -> Dict[str, int]:
        """
        Discover all PDFs for a specific year.

        Returns:
            Dict with 'total', 'new', 'existing' counts
        """
        logger.info(f"🔍 Discovering PDFs for year {year}")

        try:
            # Get PDFs list for the year
            url = f"{self.base_url}/list.php?ano={year}"
            response = self._make_request(url)

            if not response:
                return {"total": 0, "new": 0, "existing": 0}

            pdfs_data = response.json()

            if not isinstance(pdfs_data, list):
                logger.warning(
                    f"Unexpected response format for year {year}: {type(pdfs_data)}"
                )
                return {"total": 0, "new": 0, "existing": 0}

            total_count = len(pdfs_data)
            new_count = 0
            existing_count = 0

            logger.info(f"📄 Found {total_count} PDFs for year {year}")

            for pdf_info in pdfs_data:
                try:
                    if self._add_to_discovery_queue(pdf_info, year):
                        new_count += 1
                    else:
                        existing_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process PDF info for year {year}: {pdf_info}, error: {e}"
                    )
                    continue

            logger.info(f"✅ Year {year}: {new_count} new, {existing_count} existing")
            return {"total": total_count, "new": new_count, "existing": existing_count}

        except Exception as e:
            logger.error(f"Failed to discover PDFs for year {year}: {e}")
            return {"total": 0, "new": 0, "existing": 0}

    def discover_latest(self) -> Dict[str, int]:
        """Discover latest PDFs."""
        logger.info("🔍 Discovering latest PDFs")

        try:
            url = f"{self.base_url}/data-ultimo-diario.php"
            response = self._make_request(url)

            if not response:
                return {"total": 0, "new": 0, "existing": 0}

            latest_pdfs = response.json()

            if not isinstance(latest_pdfs, list):
                logger.warning(
                    f"Unexpected response format for latest PDFs: {type(latest_pdfs)}"
                )
                return {"total": 0, "new": 0, "existing": 0}

            total_count = len(latest_pdfs)
            new_count = 0
            existing_count = 0

            for pdf_info in latest_pdfs:
                try:
                    # High priority for latest PDFs
                    if self._add_to_discovery_queue(pdf_info, priority=10):
                        new_count += 1
                    else:
                        existing_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process latest PDF info: {pdf_info}, error: {e}"
                    )
                    continue

            logger.info(f"✅ Latest: {new_count} new, {existing_count} existing")
            return {"total": total_count, "new": new_count, "existing": existing_count}

        except Exception as e:
            logger.error(f"Failed to discover latest PDFs: {e}")
            return {"total": 0, "new": 0, "existing": 0}

    def discover_range(self, start_year: int, end_year: int) -> Dict[str, Dict]:
        """Discover PDFs for a range of years."""
        logger.info(f"🎯 Starting bulk discovery: {start_year} to {end_year}")

        results = {}
        total_stats = {"total": 0, "new": 0, "existing": 0}

        for year in range(start_year, end_year + 1):
            try:
                year_stats = self.discover_year(year)
                results[str(year)] = year_stats

                # Update totals
                for key in total_stats:
                    total_stats[key] += year_stats[key]

                # Rate limiting - be respectful to TJRO servers
                if year < end_year:  # Don't sleep after last year
                    logger.info("⏳ Waiting 2 seconds before next year...")
                    time.sleep(2)

            except KeyboardInterrupt:
                logger.info(f"🛑 Discovery interrupted at year {year}")
                break
            except Exception as e:
                logger.error(f"Failed to process year {year}: {e}")
                continue

        results["_totals"] = total_stats
        logger.info(f"🎉 Bulk discovery complete: {total_stats}")

        return results

    def _make_request(self, url: str, timeout: int = 30) -> requests.Response:
        """Make HTTP request with error handling."""
        try:
            logger.debug(f"📡 Requesting: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def _add_to_discovery_queue(
        self, pdf_info: Dict, year: int = None, priority: int = 0
    ) -> bool:
        """
        Add PDF info to discovery queue.

        Returns:
            True if new item was added, False if already exists
        """
        try:
            # Extract and validate required fields
            pdf_url = pdf_info.get("url", "").strip()
            if not pdf_url:
                logger.warning(f"PDF info missing URL: {pdf_info}")
                return False

            # Skip if already discovered in this session
            if pdf_url in self.discovered_urls:
                return False

            # Parse date
            year_val = year or int(pdf_info.get("year", 0))
            month_val = int(pdf_info.get("month", 0))
            day_val = int(pdf_info.get("day", 0))

            if not all([year_val, month_val, day_val]):
                logger.warning(f"Invalid date components in PDF info: {pdf_info}")
                return False

            date_str = f"{year_val}-{month_val:02d}-{day_val:02d}"
            number_str = pdf_info.get("number", "").strip()

            # Check if already in database
            existing = self.db.execute(
                """
                SELECT id FROM pdf_discovery_queue 
                WHERE url = ? OR (date = ? AND number = ?)
            """,
                (pdf_url, date_str, number_str),
            ).fetchone()

            if existing:
                return False

            # Add to queue
            self.db.execute(
                """
                INSERT INTO pdf_discovery_queue 
                (url, date, number, year, priority, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    pdf_url,
                    date_str,
                    number_str,
                    year_val,
                    priority,
                    json.dumps(pdf_info),
                ),
            )

            # Track in session
            self.discovered_urls.add(pdf_url)

            logger.debug(f"➕ Added to queue: {date_str} - {number_str}")
            return True

        except Exception as e:
            logger.error(f"Failed to add PDF to queue: {pdf_info}, error: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """Get current queue statistics."""
        stats = {}

        # Total items in discovery queue
        result = self.db.execute(
            "SELECT COUNT(*) as count FROM pdf_discovery_queue"
        ).fetchone()
        stats["total_queued"] = result[0] if result else 0

        # By status
        for status in ["pending", "processing", "completed", "failed"]:
            result = self.db.execute(
                "SELECT COUNT(*) as count FROM pdf_discovery_queue WHERE status = ?",
                (status,),
            ).fetchone()
            stats[f"{status}_count"] = result[0] if result else 0

        # By year (top 10)
        year_stats = self.db.execute("""
            SELECT year, COUNT(*) as count 
            FROM pdf_discovery_queue 
            GROUP BY year 
            ORDER BY year DESC 
            LIMIT 10
        """).fetchall()
        stats["by_year"] = {str(row[0]): row[1] for row in year_stats}

        return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover PDFs from TJRO and populate discovery queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bulk_discovery.py --start-year 1970 --end-year 2025
  python scripts/bulk_discovery.py --year 2024
  python scripts/bulk_discovery.py --latest
  python scripts/bulk_discovery.py --stats
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--start-year", type=int, help="Start year for range discovery")
    group.add_argument("--year", type=int, help="Single year to discover")
    group.add_argument(
        "--latest", action="store_true", help="Discover latest PDFs only"
    )
    group.add_argument("--stats", action="store_true", help="Show queue statistics")

    parser.add_argument(
        "--end-year",
        type=int,
        help="End year for range discovery (required with --start-year)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.start_year and not args.end_year:
        parser.error("--end-year is required when using --start-year")

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize database connection
    try:
        db = CausaGanhaDB()
        discovery = TJROPDFDiscovery(db)

        if args.stats:
            # Show statistics
            stats = discovery.get_statistics()
            print("📊 Discovery Queue Statistics:")
            print(f"  Total queued: {stats['total_queued']:,}")
            print(f"  Pending: {stats['pending_count']:,}")
            print(f"  Processing: {stats['processing_count']:,}")
            print(f"  Completed: {stats['completed_count']:,}")
            print(f"  Failed: {stats['failed_count']:,}")
            print("\n📅 By Year (Top 10):")
            for year, count in stats["by_year"].items():
                print(f"  {year}: {count:,}")
            return

        if args.dry_run:
            logger.info("🧪 DRY RUN MODE - No changes will be made")

        # Perform discovery
        start_time = datetime.now()

        if args.latest:
            results = discovery.discover_latest()
        elif args.year:
            results = discovery.discover_year(args.year)
        else:
            results = discovery.discover_range(args.start_year, args.end_year)

        end_time = datetime.now()
        duration = end_time - start_time

        # Show results
        print(f"\n🎉 Discovery completed in {duration}")
        if isinstance(results, dict) and "_totals" in results:
            totals = results["_totals"]
            print("📊 Total Results:")
            print(f"  Found: {totals['total']:,} PDFs")
            print(f"  New: {totals['new']:,}")
            print(f"  Existing: {totals['existing']:,}")
        else:
            print(f"📊 Results: {results}")

        # Final statistics
        final_stats = discovery.get_statistics()
        print("\n📈 Queue Status:")
        print(f"  Total in queue: {final_stats['total_queued']:,}")
        print(f"  Pending processing: {final_stats['pending_count']:,}")

    except KeyboardInterrupt:
        logger.info("🛑 Discovery interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
