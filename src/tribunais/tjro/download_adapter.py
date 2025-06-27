"""
TJRO-specific diario downloader adapter.

This adapter integrates the existing TJRO downloader functions
with the new Diario dataclass interface.
"""

import logging
from pathlib import Path
from typing import Optional
from models.interfaces import DiarioDownloader
from models.diario import Diario
from .downloader import fetch_tjro_pdf, archive_pdf
from datetime import date


class TJRODownloader(DiarioDownloader):
    """TJRO-specific diario downloader using existing implementation."""

    def download_diario(self, diario: Diario) -> Diario:
        """
        Download PDF and update diario with local path.

        This uses the existing fetch_tjro_pdf function but adapts it
        to work with the Diario dataclass.
        """
        if diario.tribunal != "tjro":
            raise ValueError(
                f"TJRODownloader cannot handle tribunal: {diario.tribunal}"
            )

        logging.info(f"Downloading {diario.display_name} from {diario.url}")

        try:
            # Use the existing downloader function
            pdf_path = fetch_tjro_pdf(diario.data)

            if pdf_path and pdf_path.exists():
                diario.pdf_path = pdf_path
                diario.update_status("downloaded")
                diario.metadata["download_success"] = True
                logging.info(
                    f"Successfully downloaded {diario.display_name} to {pdf_path}"
                )
            else:
                diario.metadata["download_success"] = False
                diario.metadata["error"] = "Download failed - no file created"
                logging.error(f"Failed to download {diario.display_name}")

        except Exception as e:
            diario.metadata["download_success"] = False
            diario.metadata["error"] = str(e)
            logging.error(f"Error downloading {diario.display_name}: {e}")

        return diario

    def archive_to_ia(self, diario: Diario) -> Diario:
        """
        Archive to Internet Archive and update IA identifier.

        This uses the existing archive_pdf function.
        """
        if not diario.pdf_path or not diario.pdf_path.exists():
            raise ValueError(f"PDF file not found for {diario.display_name}")

        logging.info(f"Archiving {diario.display_name} to Internet Archive")

        try:
            # Use the existing archive function
            # Note: archive_pdf expects (pdf_path, origem_url, data_publicacao, db_path)
            from pathlib import Path

            db_path = Path("data/causaganha.duckdb")  # Default path

            ia_url = archive_pdf(
                pdf_path=diario.pdf_path,
                origem_url=diario.url,
                data_publicacao=diario.data,
                db_path=db_path,
            )

            if ia_url:
                # Extract IA identifier from URL
                # IA URLs are typically: https://archive.org/details/{identifier}
                if "/details/" in ia_url:
                    diario.ia_identifier = ia_url.split("/details/")[1].split("/")[0]
                else:
                    diario.ia_identifier = ia_url

                diario.metadata["ia_url"] = ia_url
                diario.metadata["archive_success"] = True
                diario.update_status("archived")
                logging.info(f"Successfully archived {diario.display_name} to {ia_url}")
            else:
                diario.metadata["archive_success"] = False
                diario.metadata["error"] = "Archive failed - no IA URL returned"
                logging.error(f"Failed to archive {diario.display_name}")

        except Exception as e:
            diario.metadata["archive_success"] = False
            diario.metadata["error"] = str(e)
            logging.error(f"Error archiving {diario.display_name}: {e}")

        return diario

    def download_by_url(self, url: str, target_date: date) -> Optional[Path]:
        """
        Direct download by URL without using Diario object.

        This is a convenience method that wraps the existing functionality.
        """
        try:
            return fetch_tjro_pdf(target_date)
        except Exception as e:
            logging.error(f"Failed to download TJRO PDF for {target_date}: {e}")
            return None
