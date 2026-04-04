from __future__ import annotations

import httpx


HTTP_500_INTERNAL_SERVER_ERROR = 500

"""DJEN proxy client — caderno info lookup and ZIP download."""


import asyncio
import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from djen_backup.retry import request_with_retry


if TYPE_CHECKING:
    from datetime import date


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
    # Timeout of 30s is enforced by the client timeout configuration
    # in the caller, but can be overridden here if needed.
    resp = await request_with_retry(
        client,
        "GET",
        url,
        max_retries=2,
        retry_djen_400=True,
    )

    if resp.status_code == HTTP_NOT_FOUND:
        raise DJENNotFoundError(status_code=HTTP_NOT_FOUND, reason="Not Found")

    # Transient server errors (5xx, etc.) should propagate as HTTPStatusError
    # so the caller retries rather than permanently marking absent.
    if resp.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        msg = f"Server error: {resp.status_code}"
        raise httpx.HTTPError(msg)
    resp.raise_for_status()

    try:
        data: dict[str, object] = resp.json()
    except ValueError as exc:
        raise httpx.HTTPError("Invalid JSON response from DJEN proxy") from exc

    download_url = data.get("url")
    if not isinstance(download_url, str) or not download_url:
        raise httpx.HTTPError("Missing download URL in DJEN response")

    return download_url


DOWNLOAD_SEGMENTS = 4  # Number of parallel segments for large downloads
SEGMENT_THRESHOLD = 5 * 1024 * 1024  # Only segment files > 5 MB


async def _download_segment(
    client: httpx.AsyncClient,
    url: str,
    start: int,
    end: int,
    index: int,
) -> bytes:
    """Download a byte range segment."""
    headers = {"Range": f"bytes={start}-{end}"}
    async with client.stream("GET", url, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.aread()


async def download_zip(
    client: httpx.AsyncClient,
    url: str,
) -> Path:
    """Download a ZIP file to a temporary file and return its path.

    Uses parallel range requests for large files (>5MB) to speed up downloads.
    The caller is responsible for cleaning up the temp file.
    Raises :class:`DJENNotFoundError` for 404 or empty responses.
    """
    # Probe file size with a small range request
    probe = await client.get(url, headers={"Range": "bytes=0-0"})
    if probe.status_code == HTTP_NOT_FOUND:
        _raise_not_found(HTTP_NOT_FOUND, "ZIP download 404")

    content_range = probe.headers.get("content-range", "")
    total_size = 0
    if "/" in content_range:
        with contextlib.suppress(ValueError, IndexError):
            total_size = int(content_range.split("/")[1])

    filename = url.split("?", maxsplit=1)[0].rsplit("/", maxsplit=1)[-1]

    # Fallback to simple streaming if range requests not supported or file is small
    if total_size < SEGMENT_THRESHOLD:
        return await _download_simple(client, url, filename)

    size_mb = round(total_size / 1024 / 1024, 1)
    log.info("download_starting", file=filename, size_mb=size_mb, segments=DOWNLOAD_SEGMENTS)

    # Split into segments and download in parallel
    segment_size = total_size // DOWNLOAD_SEGMENTS
    tasks = []
    for i in range(DOWNLOAD_SEGMENTS):
        start = i * segment_size
        end = total_size - 1 if i == DOWNLOAD_SEGMENTS - 1 else (i + 1) * segment_size - 1
        tasks.append(_download_segment(client, url, start, end, i))

    segments = await asyncio.gather(*tasks)

    # Write all segments to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    try:
        for seg in segments:
            tmp.write(seg)
        tmp.close()
    except Exception:
        tmp.close()
        await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
        raise

    log.info("download_complete", path=tmp.name, size_mb=size_mb, segments=DOWNLOAD_SEGMENTS)
    return tmp_path


async def _download_simple(
    client: httpx.AsyncClient,
    url: str,
    filename: str,
) -> Path:
    """Simple streaming download fallback for small files or no range support."""
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    total_bytes = 0

    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code == HTTP_NOT_FOUND:
                tmp.close()
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
                _raise_not_found(HTTP_NOT_FOUND, "ZIP download 404")
            resp.raise_for_status()

            content_length = resp.headers.get("content-length")
            total_expected = int(content_length) if content_length else None
            if total_expected:
                log.info(
                    "download_starting",
                    file=filename,
                    size_mb=round(total_expected / 1024 / 1024, 1),
                )

            async for chunk in resp.aiter_bytes(chunk_size=65536):
                tmp.write(chunk)
                total_bytes += len(chunk)

        tmp.close()
        if total_bytes == 0:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
            _raise_not_found(resp.status_code, "Empty ZIP response")
    except Exception:
        tmp.close()
        await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
        raise

    log.info("download_complete", path=tmp.name, size_mb=round(total_bytes / 1024 / 1024, 1))
    return tmp_path
