"""Document service for handling PDF downloads."""

import httpx
import structlog


logger = structlog.get_logger()


class DocumentService:
    """Service for handling document operations like downloading."""

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
