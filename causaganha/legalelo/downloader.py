import datetime
import pathlib
import re
import requests
import argparse  # Added
import logging  # Added

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URL where the official diary page lists the PDF link
TJRO_DIARIO_OFICIAL_URL = "https://www.tjro.jus.br/diario_oficial/"
TJRO_LATEST_PAGE_URL = "https://www.tjro.jus.br/diario_oficial/ultimo-diario.php"

def fetch_tjro_pdf(date_obj: datetime.date) -> pathlib.Path | None: # Adjusted return type hint
    """
    Downloads the Diário da Justiça PDF for the given date from TJRO.

    Args:
        date_obj: A datetime.date object representing the desired date.

    Returns:
        A pathlib.Path object pointing to the downloaded PDF file.
        Returns None if download fails.
    """
    file_name = f"dj_{date_obj.strftime('%Y%m%d')}.pdf"

    output_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "diarios"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name

    logging.info(
        f"Attempting to locate PDF for {date_obj.strftime('%Y-%m-%d')} from {TJRO_DIARIO_OFICIAL_URL}"
    )

    date_str = date_obj.strftime("%Y%m%d")

    try:
        page_resp = requests.get(TJRO_DIARIO_OFICIAL_URL, timeout=30)
        page_resp.raise_for_status()
        pdf_match = re.search(
            rf"https://www\.tjro\.jus\.br/novodiario/\d{{4}}/[^\"']*{date_str}[^\"']*\.pdf",
            page_resp.text,
        )
        if not pdf_match:
            logging.error(f"Could not find PDF link for date {date_str} on page.")
            return None
        download_url = pdf_match.group(0)
        logging.info(f"Found diary link: {download_url}")
        pdf_resp = requests.get(download_url, timeout=30)
        pdf_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(pdf_resp.content)
        logging.info(f"Successfully downloaded {output_path}")
        return output_path
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Error downloading PDF for {date_obj.strftime('%Y-%m-%d')}: {e}")
        return None

def fetch_latest_tjro_pdf() -> pathlib.Path | None:
    """Downloads the most recent Diário da Justiça PDF available."""
    logging.info(f"Fetching latest diary page from {TJRO_LATEST_PAGE_URL}")
    try:
        page_resp = requests.get(TJRO_LATEST_PAGE_URL, timeout=30)
        page_resp.raise_for_status()
        match = re.search(r"https://www\.tjro\.jus\.br/novodiario/\d{4}/[^'\"]+\.pdf", page_resp.text)
        if not match:
            logging.error("Could not locate PDF link on latest diary page")
            return None
        download_url = match.group(0)
        date_match = re.search(r"(\d{8})", download_url)
        file_date = date_match.group(1) if date_match else datetime.date.today().strftime("%Y%m%d")
        return fetch_tjro_pdf(datetime.datetime.strptime(file_date, "%Y%m%d").date())
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching latest diary page: {e}")
        return None

def main(): # Added main function for CLI
    parser = argparse.ArgumentParser(description="Download Diário da Justiça PDF from TJRO for a specific date.")
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="The date for which to download the Diário, in YYYY-MM-DD format."
    )

    args = parser.parse_args()

    try:
        selected_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    logging.info(f"Running downloader for date: {selected_date.strftime('%Y-%m-%d')}")
    file_path = fetch_tjro_pdf(selected_date)

    if file_path:
        logging.info(f"PDF downloaded to: {file_path}")
    else:
        logging.warning(f"Failed to download PDF for {selected_date.strftime('%Y-%m-%d')}")

if __name__ == '__main__':
    main()
