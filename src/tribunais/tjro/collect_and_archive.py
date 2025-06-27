"""
Collect and archive TJRO judicial documents.

This module provides functionality to download TJRO PDFs for specific dates
or the latest available documents, then archive them to Internet Archive.
"""

import datetime
import logging
import re
from pathlib import Path
from typing import Optional

from .downloader import (
    fetch_tjro_pdf,
    fetch_latest_tjro_pdf,
    archive_pdf,
)


def collect_and_archive_diario(
    date: Optional[str] = None,
    latest: bool = False,
    db_path: Path = Path("data/causaganha.duckdb"),
) -> Optional[str]:
    """
    Download and archive a TJRO diario for a specific date or latest available.
    
    Args:
        date: Date in YYYY-MM-DD format to collect
        latest: If True, fetch the latest available PDF
        db_path: Path to DuckDB database file
        
    Returns:
        Internet Archive URL if successful, None if failed
    """
    pdf_filepath: Optional[Path] = None
    origem_url: Optional[str] = None
    data_publicacao: Optional[datetime.date] = None

    if latest:
        logging.info("Fetching the latest TJRO PDF.")
        pdf_filepath, origem_url = fetch_latest_tjro_pdf()
        if pdf_filepath:
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
            return None

    elif date:
        try:
            data_publicacao = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            logging.info(f"Fetching TJRO PDF for date: {data_publicacao}.")
            pdf_filepath, origem_url = fetch_tjro_pdf(data_publicacao)
            if not pdf_filepath:
                logging.error(f"Failed to download PDF for {data_publicacao}.")
                return None
        except ValueError:
            logging.error(f"Invalid date format: '{date}'. Please use YYYY-MM-DD.")
            return None
    else:
        # Default to fetching yesterday's PDF if no specific date or latest is given
        data_publicacao = datetime.date.today() - datetime.timedelta(days=1)
        logging.info(
            f"No date or latest flag specified. Fetching PDF for yesterday: {data_publicacao}."
        )
        pdf_filepath, origem_url = fetch_tjro_pdf(data_publicacao)
        if not pdf_filepath:
            logging.error(f"Failed to download PDF for yesterday ({data_publicacao}).")
            return None

    if not pdf_filepath or not pdf_filepath.exists():
        logging.error(
            f"PDF file path is invalid or file does not exist: {pdf_filepath}. Cannot archive."
        )
        return None

    if not data_publicacao:
        logging.error(
            "Publication date could not be determined. Cannot archive without publication date."
        )
        return None

    # TODO: Implement "SegredoDeJustica" check here before archiving.
    # This would involve analyzing the PDF content or metadata if available.

    logging.info(f"Proceeding to archive PDF: {pdf_filepath}")
    logging.info(f"  Original URL: {origem_url}")
    logging.info(f"  Publication Date: {data_publicacao}")
    logging.info(f"  Database Path: {db_path}")

    archive_ia_url = archive_pdf(
        pdf_path=pdf_filepath,
        origem_url=origem_url,
        data_publicacao=data_publicacao,
        db_path=db_path,
    )

    if archive_ia_url:
        logging.info(
            f"Successfully archived {pdf_filepath.name} to Internet Archive: {archive_ia_url}"
        )
        return archive_ia_url
    else:
        logging.error(f"Failed to archive {pdf_filepath.name} to Internet Archive.")
        return None