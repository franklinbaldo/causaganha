"""
TJRO-specific diario URL discovery implementation.
"""

import requests
import re
import logging
from datetime import date
from typing import Optional, List
from models.interfaces import DiarioDiscovery


class TJRODiscovery(DiarioDiscovery):
    """TJRO-specific diario URL discovery."""

    TJRO_BASE_URL = "https://www.tjro.jus.br/diario_oficial/"
    TJRO_LATEST_URL = "https://www.tjro.jus.br/diario_oficial/ultimo-diario.php"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    @property
    def tribunal_code(self) -> str:
        """Return the tribunal code."""
        return "tjro"

    def get_diario_url(self, target_date: date) -> Optional[str]:
        """
        Get diario URL for specific date.

        This implementation reuses the existing logic from downloader.py
        get_tjro_pdf_url function.
        """
        date_str = target_date.strftime("%Y%m%d")

        try:
            response = requests.get(
                self.TJRO_BASE_URL, headers=self.headers, timeout=30
            )
            response.raise_for_status()

            # Use the same regex pattern as the existing downloader
            pdf_match = re.search(
                rf"https://www\.tjro\.jus\.br/novodiario/\d{{4}}/[^\"']*{date_str}[^\"']*\.pdf",
                response.text,
            )

            if pdf_match:
                url = pdf_match.group(0)
                logging.info(f"Found TJRO diario URL for {target_date}: {url}")
                return url
            else:
                logging.warning(f"No TJRO diario found for date {target_date}")
                return None

        except requests.RequestException as e:
            logging.error(f"Error finding TJRO diario URL for {target_date}: {e}")
            return None

    def get_latest_diario_url(self) -> Optional[str]:
        """
        Get URL for the most recent available diario.

        This implementation is based on the existing fetch_latest_tjro_pdf logic.
        """
        try:
            response = requests.get(
                self.TJRO_LATEST_URL, headers=self.headers, timeout=30
            )
            response.raise_for_status()

            # Look for PDF links in the latest page
            pdf_match = re.search(
                r"https://www\.tjro\.jus\.br/novodiario/\d{4}/[^\"']*\.pdf",
                response.text,
            )

            if pdf_match:
                url = pdf_match.group(0)
                logging.info(f"Found latest TJRO diario URL: {url}")
                return url
            else:
                logging.warning("No latest TJRO diario found")
                return None

        except requests.RequestException as e:
            logging.error(f"Error finding latest TJRO diario URL: {e}")
            return None

    def list_diarios_in_range(self, start_date: date, end_date: date) -> List[str]:
        """
        Get URLs for all diarios in date range.

        For TJRO, we use the default implementation that checks each date
        individually, but we could optimize this in the future by scraping
        the archive pages directly.
        """
        logging.info(f"Discovering TJRO diarios from {start_date} to {end_date}")

        # Use the parent implementation for now
        urls = super().list_diarios_in_range(start_date, end_date)

        logging.info(f"Found {len(urls)} TJRO diarios in date range")
        return urls

    def get_diario_metadata(self, url: str) -> dict:
        """
        Extract additional metadata from TJRO diario URL.

        TJRO URLs contain useful information like year and edition number.
        """
        metadata = {}

        # Extract year from URL pattern
        year_match = re.search(r"/novodiario/(\d{4})/", url)
        if year_match:
            metadata["year"] = int(year_match.group(1))

        # Extract date from filename if possible
        date_match = re.search(r"(\d{8})", url)
        if date_match:
            metadata["date_str"] = date_match.group(1)

        # Extract any edition number if present
        edition_match = re.search(r"[-_]?(\d+)[-_]?[^/]*\.pdf$", url)
        if edition_match:
            metadata["edition"] = edition_match.group(1)

        return metadata
