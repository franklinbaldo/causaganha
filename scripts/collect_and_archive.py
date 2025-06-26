# ruff: noqa: E402
import argparse
import datetime
import logging
import sys
from pathlib import Path
from typing import Optional

# Add src directory to sys.path to allow importing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from downloader import (
    fetch_tjro_pdf,
    fetch_latest_tjro_pdf,
    archive_pdf,
)  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a TJRO PDF for a specific date or the latest available, then archive it to Internet Archive."
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date in YYYY-MM-DD format to collect. If not provided, --latest must be used or defaults to yesterday.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Fetch the latest available PDF. Overrides --date if both are provided.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/causaganha.duckdb"),  # Default path for the DuckDB database
        help="Path to DuckDB database file.",
    )
    args = parser.parse_args()

    # Setup enhanced logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d %(funcName)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    pdf_filepath: Optional[Path] = None
    origem_url: Optional[str] = None
    data_publicacao: Optional[datetime.date] = (
        None  # This will be the date of the diary
    )

    if args.latest:
        logging.info("Fetching the latest TJRO PDF.")
        pdf_filepath, origem_url = fetch_latest_tjro_pdf()
        if pdf_filepath:
            # Try to determine data_publicacao from filename if possible, otherwise, it might remain None
            # or could default to today if that's acceptable for "latest"
            # For now, if fetch_latest gives a file, we assume its publication date is "today" or needs parsing
            # The downloader's fetch_latest_tjro_pdf was modified to try and parse date from filename
            # For simplicity here, we'll assume if a date is needed for archive_pdf, it's derived or passed.
            # Let's try to parse from filename or use today.
            # A more robust way would be for fetch_latest_tjro_pdf to also return the determined date.
            # For now, we will use the file's presumed date if filename parsing worked, or today.
            try:
                # Attempt to parse date from filename like dj_YYYYMMDD.pdf
                parsed_date_match = re.search(
                    r"dj_(\d{4})(\d{2})(\d{2})", pdf_filepath.name
                )
                if parsed_date_match:
                    year, month, day = map(int, parsed_date_match.groups())
                    data_publicacao = datetime.date(year, month, day)
                    logging.info(
                        f"Determined publication date from filename for latest PDF: {data_publicacao}"
                    )
                else:
                    data_publicacao = datetime.date.today()  # Fallback for latest
                    logging.warning(
                        f"Could not determine exact publication date for latest PDF from filename {pdf_filepath.name}. Using today: {data_publicacao}"
                    )
            except Exception as e:
                logging.warning(
                    f"Error parsing date from latest PDF filename {pdf_filepath.name if pdf_filepath else 'N/A'}: {e}. Using today."
                )
                data_publicacao = datetime.date.today()
        else:
            logging.error("Failed to fetch the latest PDF.")
            return  # Exit if download failed

    elif args.date:
        try:
            data_publicacao = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
            logging.info(f"Fetching TJRO PDF for date: {data_publicacao}.")
            pdf_filepath, origem_url = fetch_tjro_pdf(data_publicacao)
            if not pdf_filepath:
                logging.error(f"Failed to download PDF for {data_publicacao}.")
                return  # Exit if download failed
        except ValueError:
            logging.error(f"Invalid date format: '{args.date}'. Please use YYYY-MM-DD.")
            return
    else:
        # Default to fetching yesterday's PDF if no specific date or --latest is given
        # This is useful for automated nightly runs.
        data_publicacao = datetime.date.today() - datetime.timedelta(days=1)
        logging.info(
            f"No date or --latest flag specified. Fetching PDF for yesterday: {data_publicacao}."
        )
        pdf_filepath, origem_url = fetch_tjro_pdf(data_publicacao)
        if not pdf_filepath:
            logging.error(f"Failed to download PDF for yesterday ({data_publicacao}).")
            return  # Exit if download failed

    if not pdf_filepath or not pdf_filepath.exists():
        logging.error(
            f"PDF file path is invalid or file does not exist: {pdf_filepath}. Cannot archive."
        )
        return

    if not data_publicacao:
        logging.error(
            "Publication date could not be determined. Cannot archive without publication date."
        )
        # Potentially try to parse from filename as a last resort if not already done for 'latest'
        # For now, exiting.
        return

    # TODO: Implement "SegredoDeJustica" check here before archiving.
    # This would involve analyzing the PDF content or metadata if available.
    # For example:
    # if check_for_segredo(pdf_filepath):
    #     logging.info(f"PDF {pdf_filepath} is marked as Segredo de Justiça. Skipping archival.")
    #     return

    logging.info(f"Proceeding to archive PDF: {pdf_filepath}")
    logging.info(f"  Original URL: {origem_url}")
    logging.info(f"  Publication Date: {data_publicacao}")
    logging.info(f"  Database Path: {args.db_path}")

    archive_ia_url = archive_pdf(
        pdf_path=pdf_filepath,
        origem_url=origem_url,
        data_publicacao=data_publicacao,
        db_path=args.db_path,
    )

    if archive_ia_url:
        logging.info(
            f"Successfully archived {pdf_filepath.name} to Internet Archive: {archive_ia_url}"
        )
    else:
        logging.error(f"Failed to archive {pdf_filepath.name} to Internet Archive.")


if __name__ == "__main__":
    # This import is here because it's only needed if trying to parse date from filename for --latest
    # and to avoid circular dependencies or premature imports if not strictly needed at module level.
    import re

    main()
