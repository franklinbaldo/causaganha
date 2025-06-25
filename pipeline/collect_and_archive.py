import argparse
import datetime
import logging
from pathlib import Path

from causaganha.core.downloader import fetch_tjro_pdf, archive_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a TJRO PDF and archive to Internet Archive"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format to collect (default: today)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/causaganha.duckdb"),
        help="Path to DuckDB database",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.date:
        date_obj = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        date_obj = datetime.date.today()

    pdf_path = fetch_tjro_pdf(date_obj)
    if not pdf_path:
        logging.error("Failed to download PDF for %s", date_obj)
        return

    archive_url = archive_pdf(pdf_path, args.db_path)
    logging.info("Archived %s to %s", pdf_path, archive_url)


if __name__ == "__main__":
    main()

