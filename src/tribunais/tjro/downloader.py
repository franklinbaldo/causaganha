import datetime
import pathlib
import re
import requests
import logging
import hashlib
import subprocess
from typing import Optional

__all__ = ["get_tjro_pdf_url", "fetch_tjro_pdf", "fetch_latest_tjro_pdf"]

# Base URLs for TJRO Diário
TJRO_DIARIO_OFICIAL_URL = "https://www.tjro.jus.br/diario_oficial/"
TJRO_LATEST_PAGE_URL = "https://www.tjro.jus.br/diario_oficial/ultimo-diario.php"

def get_tjro_pdf_url(date_obj: datetime.date) -> Optional[str]:
    """
    Get the PDF URL for the given date from TJRO without downloading.

    Returns:
        The URL string or None if not found or on error.
    """
    date_str = date_obj.strftime("%Y%m%d")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    try:
        resp = requests.get(TJRO_DIARIO_OFICIAL_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        pattern = rf"https://www\.tjro\.jus\.br/novodiario/\d{{4}}/[^\"]*{date_str}[^\"]*\.pdf"
        m = re.search(pattern, resp.text)
        if not m:
            logging.error(f"Could not find PDF link for date {date_str} on page.")
            return None
        url = m.group(0)
        logging.info(f"Found diary link: {url}")
        return url
    except requests.RequestException as e:
        logging.error(f"Error finding PDF URL for {date_str}: {e}")
        return None

def fetch_tjro_pdf(
    date_obj: datetime.date, output_dir: Optional[pathlib.Path] = None
) -> Optional[pathlib.Path]:
    """
    Download the TJRO Diário PDF for a specific date.

    Returns:
        The local Path or None on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    if output_dir is None:
        output_dir = pathlib.Path(__file__).parent.parent / "data" / "diarios"
    output_dir.mkdir(parents=True, exist_ok=True)

    url = get_tjro_pdf_url(date_obj)
    if not url:
        return None

    file_name = f"dj_{date_obj.strftime('%Y%m%d')}.pdf"
    dest = output_dir / file_name
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        logging.info(f"Downloaded PDF to {dest}")
        return dest
    except requests.RequestException as e:
        logging.error(f"Error downloading PDF for {date_obj}: {e}")
        return None

def fetch_latest_tjro_pdf(output_dir: Optional[pathlib.Path] = None) -> Optional[pathlib.Path]:
    """
    Download the latest TJRO Diário PDF via redirect.

    Returns:
        The local Path or None on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    }
    if output_dir is None:
        output_dir = pathlib.Path(__file__).parent.parent / "data" / "diarios"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            TJRO_LATEST_PAGE_URL, headers=headers, timeout=30, allow_redirects=False
        )
        if resp.status_code != 302 or "Location" not in resp.headers:
            logging.error(f"Expected redirect, got {resp.status_code}")
            return None
        pdf_url = resp.headers["Location"]
        if not pdf_url.startswith("http"):
            pdf_url = f"https://www.tjro.jus.br{pdf_url}"

        logging.info(f"Found latest diary URL: {pdf_url}")
        m = re.search(r"/([^/]+\.pdf)$", pdf_url)
        fn = m.group(1) if m else f"dj_{datetime.date.today().strftime('%Y%m%d')}.pdf"
        dest = output_dir / fn

        pdf_resp = requests.get(pdf_url, headers=headers, timeout=30)
        pdf_resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(pdf_resp.content)
        logging.info(f"Downloaded latest PDF to {dest}")
        return dest
    except requests.RequestException as e:
        logging.error(f"Error downloading latest diary: {e}")
        return None
