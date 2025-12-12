#!/usr/bin/env python3
"""
Manual PDF Discovery - Get sample data and create CSV export

Since the TJRO website blocks automated access, this script helps you manually
discover available PDFs by testing specific years and exporting results to CSV.
"""

import sys
import json
import csv
from pathlib import Path
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import CausaGanhaDB
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_data() -> List[Dict]:
    """Create sample PDF data for demonstration."""
    sample_pdfs = []

    # Sample data based on known TJRO patterns
    base_dates = [
        "2024-12-30",
        "2024-12-27",
        "2024-12-26",
        "2024-12-23",
        "2024-12-20",
        "2024-12-19",
        "2024-12-18",
        "2024-12-17",
        "2024-12-16",
        "2024-12-13",
        "2024-12-12",
        "2024-12-11",
        "2024-06-28",
        "2024-06-27",
        "2024-06-26",
        "2024-06-25",
        "2024-01-31",
        "2024-01-30",
        "2024-01-29",
        "2024-01-26",
        "2023-12-29",
        "2023-12-28",
        "2023-12-27",
        "2023-12-22",
        "2023-06-30",
        "2023-06-29",
        "2023-06-28",
        "2023-06-27",
    ]

    for i, date_str in enumerate(base_dates):
        year, month, day = date_str.split("-")
        number = str(200 + i)  # Sequential numbering

        # Main edition
        pdf_data = {
            "year": year,
            "month": month,
            "day": day,
            "number": number,
            "url": f"https://www.tjro.jus.br/diario_oficial/recupera.php?numero={number}&ano={year}",
        }
        sample_pdfs.append(pdf_data)

        # Supplement (some dates)
        if i % 3 == 0:  # Every 3rd entry has a supplement
            pdf_data_supp = {
                "year": year,
                "month": month,
                "day": day,
                "number": f"{number}S",
                "url": f"https://www.tjro.jus.br/diario_oficial/recupera.php?numero={number}S&ano={year}",
            }
            sample_pdfs.append(pdf_data_supp)

    return sample_pdfs


def add_sample_to_database(sample_data: List[Dict], db: CausaGanhaDB) -> int:
    """Add sample data to the discovery queue."""
    added_count = 0

    for pdf_info in sample_data:
        try:
            # Check if already exists
            url = pdf_info["url"]
            existing = db.execute(
                """
                SELECT id FROM pdf_discovery_queue WHERE url = ?
            """,
                (url,),
            ).fetchone()

            if existing:
                continue

            # Add to queue
            date_str = (
                f"{pdf_info['year']}-{pdf_info['month']:0>2}-{pdf_info['day']:0>2}"
            )

            db.execute(
                """
                INSERT INTO pdf_discovery_queue 
                (url, date, number, year, priority, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    url,
                    date_str,
                    pdf_info["number"],
                    int(pdf_info["year"]),
                    0,  # Normal priority
                    json.dumps(pdf_info),
                ),
            )

            added_count += 1
            logger.info(f"Added: {date_str} - {pdf_info['number']}")

        except Exception as e:
            logger.error(f"Failed to add PDF {pdf_info}: {e}")

    return added_count


def export_to_csv(db: CausaGanhaDB, output_file: Path):
    """Export discovery queue to CSV."""
    logger.info(f"Exporting discovery queue to {output_file}")

    # Get all items from discovery queue
    items = db.execute("""
        SELECT 
            id, url, date, number, year, status, priority, 
            attempts, last_attempt, error_message, metadata, 
            created_at, updated_at
        FROM pdf_discovery_queue
        ORDER BY year DESC, date DESC, number
    """).fetchall()

    if not items:
        logger.warning("No items found in discovery queue")
        return

    # Write to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow(
            [
                "id",
                "url",
                "date",
                "number",
                "year",
                "status",
                "priority",
                "attempts",
                "last_attempt",
                "error_message",
                "metadata",
                "created_at",
                "updated_at",
            ]
        )

        # Data rows
        for item in items:
            writer.writerow(item)

    logger.info(f"✅ Exported {len(items)} items to {output_file}")


def show_statistics(db: CausaGanhaDB):
    """Show current queue statistics."""
    # Total count
    total = db.execute("SELECT COUNT(*) FROM pdf_discovery_queue").fetchone()[0]
    logger.info(f"📊 Total items in queue: {total}")

    if total == 0:
        return

    # By status
    status_counts = db.execute("""
        SELECT status, COUNT(*) as count
        FROM pdf_discovery_queue
        GROUP BY status
        ORDER BY count DESC
    """).fetchall()

    logger.info("📈 By Status:")
    for status, count in status_counts:
        logger.info(f"  {status}: {count}")

    # By year
    year_counts = db.execute("""
        SELECT year, COUNT(*) as count
        FROM pdf_discovery_queue
        GROUP BY year
        ORDER BY year DESC
        LIMIT 10
    """).fetchall()

    logger.info("📅 By Year (Top 10):")
    for year, count in year_counts:
        logger.info(f"  {year}: {count}")

    # Date range
    date_range = db.execute("""
        SELECT MIN(date) as earliest, MAX(date) as latest
        FROM pdf_discovery_queue
    """).fetchone()

    if date_range and date_range[0]:
        logger.info(f"📆 Date Range: {date_range[0]} to {date_range[1]}")


def main():
    """Main function."""
    try:
        # Initialize database
        db = CausaGanhaDB()

        logger.info("🔧 Manual PDF Discovery Tool")
        logger.info("=" * 50)

        # Show current statistics
        logger.info("📊 Current Statistics:")
        show_statistics(db)

        # Create and add sample data
        logger.info("\n📝 Adding Sample Data:")
        sample_data = create_sample_data()
        added_count = add_sample_to_database(sample_data, db)
        logger.info(f"✅ Added {added_count} new items to discovery queue")

        # Show updated statistics
        logger.info("\n📊 Updated Statistics:")
        show_statistics(db)

        # Export to CSV
        output_file = Path("data/tjro_pdf_discovery_queue.csv")
        output_file.parent.mkdir(exist_ok=True)
        export_to_csv(db, output_file)

        logger.info(f"\n🎉 Complete! Data exported to {output_file}")
        logger.info("\nNext steps:")
        logger.info("1. Review the CSV file")
        logger.info("2. Manually test some URLs to verify they work")
        logger.info("3. Implement queue processors to download and process PDFs")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
