import datetime
import pathlib
import requests
import argparse # Added
import logging # Added

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Updated TJRO Diário da Justiça PDF base URL
TJRO_DIARIO_BASE_URL = "https://www.tjro.jus.br/diariodajustica/diario/"

def fetch_tjro_pdf(date_obj: datetime.date) -> pathlib.Path | None: # Adjusted return type hint
    """
    Downloads the Diário da Justiça PDF for the given date from TJRO.

    Args:
        date_obj: A datetime.date object representing the desired date.

    Returns:
        A pathlib.Path object pointing to the downloaded PDF file.
        Returns None if download fails.
    """
    # Updated file_name format
    file_name = f"dj_{date_obj.strftime('%Y%m%d')}.pdf"

    # Construct the full download URL
    download_url = f"{TJRO_DIARIO_BASE_URL}{file_name}"

    output_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "diarios"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name

    logging.info(f"Attempting to download PDF for {date_obj.strftime('%Y-%m-%d')} from {download_url}") # Log the actual URL
    logging.info(f"Saving to: {output_path}")

    try:
        # Use the constructed download_url
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Successfully downloaded {output_path}")
        return output_path
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading PDF for {date_obj.strftime('%Y-%m-%d')}: {e}")
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
