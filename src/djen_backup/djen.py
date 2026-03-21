"""DJEN proxy client — caderno info lookup and ZIP download."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from djen_backup.retry import request_with_retry


if TYPE_CHECKING:
    from datetime import date

    import httpx

log = structlog.get_logger()


def _raise_not_found(status_code: int, reason: str) -> None:
    """Helper to raise DJENNotFoundError (satisfies TRY301)."""
    raise DJENNotFoundError(status_code=status_code, reason=reason)


# HTTP status constants
HTTP_NOT_FOUND = 404


class DJENNotFoundError(Exception):
    """Raised when the DJEN proxy returns 404 or an empty response."""

    def __init__(self, status_code: int, reason: str) -> None:
        """Initialize the exception with status code and reason."""
        super().__init__(reason)
        self.status_code = status_code
        self.reason = reason


async def get_caderno_url(
    client: httpx.AsyncClient,
    base_url: str,
    tribunal: str,
    d: date,
) -> str:
    """Return the ZIP download URL for a given tribunal/date.

    Raises :class:`DJENNotFoundError` when the caderno is unavailable.
    """
    url = f"{base_url}/api/v1/caderno/{tribunal}/{d.isoformat()}/D"
    resp = await request_with_retry(client, "GET", url, retry_djen_400=True)

    if resp.status_code == HTTP_NOT_FOUND:
        raise DJENNotFoundError(status_code=HTTP_NOT_FOUND, reason="Not Found")

    # Transient server errors (5xx, etc.) should propagate as HTTPStatusError
    # so the caller retries rather than permanently marking absent.
    if resp.status_code >= 500:
        import httpx

        raise httpx.HTTPError(f"Server error: {resp.status_code}")
    resp.raise_for_status()

    try:
        data: dict[str, object] = resp.json()
    except ValueError as exc:
        raise DJENNotFoundError(status_code=resp.status_code, reason="Invalid JSON") from exc

    download_url = data.get("url")
    if not isinstance(download_url, str) or not download_url:
        raise DJENNotFoundError(status_code=resp.status_code, reason="Empty or missing URL field")

    return download_url


async def download_zip(
    client: httpx.AsyncClient,
    url: str,
) -> Path:
    """Download a ZIP file to a temporary file and return its path.

    Uses streaming to handle large files efficiently and logs progress.
    The caller is responsible for cleaning up the temp file.
    Raises :class:`DJENNotFoundError` for 404 or empty responses.
    """
    # Create temp file first
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)  # noqa: SIM115
    tmp_path = Path(tmp.name)
    total_bytes = 0
    last_logged_mb = 0
    progress_interval_mb = 10  # Log every 10MB

    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code == HTTP_NOT_FOUND:
                tmp.close()
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
                _raise_not_found(HTTP_NOT_FOUND, "ZIP download 404")

            resp.raise_for_status()

            # Get content length if available
            content_length = resp.headers.get("content-length")
            total_expected = int(content_length) if content_length else None

            if total_expected:
                filename = url.rsplit("/", maxsplit=1)[-1]
                log.info(
                    "download_starting",
                    file=filename,
                    size_mb=round(total_expected / 1024 / 1024, 1),
                )

            async for chunk in resp.aiter_bytes(chunk_size=65536):
                tmp.write(chunk)
                total_bytes += len(chunk)

                # Log progress every N MB
                current_mb = total_bytes // (1024 * 1024)
                if current_mb >= last_logged_mb + progress_interval_mb:
                    last_logged_mb = current_mb
                    if total_expected:
                        pct = round(100 * total_bytes / total_expected, 1)
                        log.info(
                            "download_progress",
                            downloaded_mb=current_mb,
                            total_mb=round(total_expected / 1024 / 1024, 1),
                            percent=pct,
                        )
                    else:
                        log.info("download_progress", downloaded_mb=current_mb)

        tmp.close()

        if total_bytes == 0:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
            _raise_not_found(resp.status_code, "Empty ZIP response")

    except Exception:
        tmp.close()
        await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
        raise

    log.info(
        "download_complete",
        path=tmp.name,
        size_mb=round(total_bytes / 1024 / 1024, 1),
    )
    return tmp_path
