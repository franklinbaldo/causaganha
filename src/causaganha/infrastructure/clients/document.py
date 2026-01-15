"""Document service for handling PDF downloads."""

import httpx
import structlog


logger = structlog.get_logger()


import io
from PyPDF2 import PdfReader

class DocumentService:
    """Service for handling document operations like downloading and text extraction."""

    async def download_pdf(self, url: str) -> bytes | None:
        """Download PDF from URL.

        Args:
            url: The URL to download from.

        Returns:
            The content bytes or None if failed.
        """
        async with httpx.AsyncClient() as client:
            try:
                # Using client.request to avoid type checking issues with dynamic get method
                resp = await client.request("GET", url, follow_redirects=True, timeout=30.0)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "application/pdf" not in content_type and not url.lower().endswith(".pdf"):
                    logger.warning("url_not_pdf", url=url, content_type=content_type)
                return resp.content
            except Exception:
                logger.exception("download_failed", url=url)
                return None

    async def extract_text_from_pdf(self, pdf_bytes: bytes) -> list[str]:
        """Extracts text from PDF bytes, page by page.

        Args:
            pdf_bytes: The byte content of the PDF.

        Returns:
            A list of strings, where each string is the text of a page.
        """
        try:
            with io.BytesIO(pdf_bytes) as f:
                reader = PdfReader(f)
                pages_text = [page.extract_text() for page in reader.pages]
                return pages_text
        except Exception:
            logger.exception("pdf_text_extraction_failed")
            return []

