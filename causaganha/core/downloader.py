import datetime
import pathlib
import re
import requests
import argparse
import logging
import hashlib
import subprocess
import duckdb

# URL where the official diary page lists the PDF link
TJRO_DIARIO_OFICIAL_URL = "https://www.tjro.jus.br/diario_oficial/"
TJRO_LATEST_PAGE_URL = "https://www.tjro.jus.br/diario_oficial/ultimo-diario.php"


def fetch_tjro_pdf(
    date_obj: datetime.date,
) -> pathlib.Path | None:  # Adjusted return type hint
    """
    Downloads the Diário da Justiça PDF for the given date from TJRO.

    Args:
        date_obj: A datetime.date object representing the desired date.

    Returns:
        A pathlib.Path object pointing to the downloaded PDF file.
        Returns None if download fails.
    """
    file_name = f"dj_{date_obj.strftime('%Y%m%d')}.pdf"

    output_dir = pathlib.Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name

    logging.info(
        f"Attempting to locate PDF for {date_obj.strftime('%Y-%m-%d')} from {TJRO_DIARIO_OFICIAL_URL}"
    )

    date_str = date_obj.strftime("%Y%m%d")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        page_resp = requests.get(TJRO_DIARIO_OFICIAL_URL, headers=headers, timeout=30)
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
        pdf_resp = requests.get(download_url, headers=headers, timeout=30)
        pdf_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(pdf_resp.content)
        logging.info(f"Successfully downloaded {output_path}")
        return output_path
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading PDF for {date_obj.strftime('%Y-%m-%d')}: {e}")
        return None


def fetch_latest_tjro_pdf() -> pathlib.Path | None:
    """Downloads the most recent Diário da Justiça PDF available."""
    logging.info(f"Fetching latest diary from {TJRO_LATEST_PAGE_URL}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # The ultimo-diario.php URL directly redirects to the PDF file
    output_dir = pathlib.Path("data")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # First request to get the redirect URL
        response = requests.get(
            TJRO_LATEST_PAGE_URL, headers=headers, timeout=30, allow_redirects=False
        )

        if response.status_code == 302 and "Location" in response.headers:
            pdf_url = response.headers["Location"]
            if not pdf_url.startswith("http"):
                pdf_url = f"https://www.tjro.jus.br{pdf_url}"

            logging.info(f"Found PDF URL: {pdf_url}")

            # Extract date from filename for output file
            filename_match = re.search(r"/([^/]+\.pdf)$", pdf_url)
            if filename_match:
                filename = filename_match.group(1)
                # Try to extract date from filename (format: YYYYMMDDXXXX-NRXXX.pdf)
                date_match = re.search(r"(\d{8})", filename)
                if date_match:
                    date_str = date_match.group(1)
                    file_name = f"dj_{date_str}.pdf"
                else:
                    file_name = filename
            else:
                file_name = f"dj_{datetime.date.today().strftime('%Y%m%d')}.pdf"

            output_path = output_dir / file_name

            # Download the PDF
            pdf_response = requests.get(pdf_url, headers=headers, timeout=30)
            pdf_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(pdf_response.content)

            logging.info(f"Successfully downloaded {output_path}")
            return output_path
        else:
            logging.error(f"Expected redirect but got status {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching latest diary: {e}")
        return None


def archive_pdf(
    pdf_path: pathlib.Path,
    db_path: pathlib.Path = pathlib.Path("data/causaganha.duckdb"),
) -> str | None:
    """Upload a PDF to the Internet Archive and record the link in DuckDB."""

    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    item_id = f"cg-{sha[:12]}"
    filename = pdf_path.name

    exists = (
        subprocess.run(
            ["ia", "metadata", item_id, "--raw"], capture_output=True, text=True
        ).returncode
        == 0
    )

    if not exists:
        subprocess.check_call(
            [
                "ia",
                "upload",
                item_id,
                str(pdf_path),
                "--metadata",
                "mediatype:texts",
                "--metadata",
                "subject:causa_ganha, trj:ro",
                "--metadata",
                f"sha256:{sha}",
                "--retries",
                "5",
            ]
        )

    archive_url = f"https://archive.org/download/{item_id}/{filename}"

    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS pdfs (
            sha256 TEXT PRIMARY KEY,
            item_id TEXT,
            ia_url TEXT
        );
        """
    )
    con.execute(
        "INSERT OR IGNORE INTO pdfs VALUES (?, ?, ?)",
        (sha, item_id, archive_url),
    )
    con.close()

    return archive_url


def main():  # Added main function for CLI
    parser = argparse.ArgumentParser(
        description="Download Diário da Justiça PDF from TJRO."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--date",
        type=str,
        help="The date for which to download the Diário, in YYYY-MM-DD format.",
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Download the most recent Diário available.",
    )

    args = parser.parse_args()

    if args.latest:
        logging.info("Running downloader for latest diary")
        file_path = fetch_latest_tjro_pdf()
    else:
        try:
            selected_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logging.error("Invalid date format. Please use YYYY-MM-DD.")
            return

        logging.info(
            f"Running downloader for date: {selected_date.strftime('%Y-%m-%d')}"
        )
        file_path = fetch_tjro_pdf(selected_date)

    if file_path:
        logging.info(f"PDF downloaded to: {file_path}")
    else:
        if args.latest:
            logging.warning("Failed to download latest Diário")
        else:
            logging.warning(
                f"Failed to download PDF for {selected_date.strftime('%Y-%m-%d')}"
            )


if __name__ == "__main__":
    main()
