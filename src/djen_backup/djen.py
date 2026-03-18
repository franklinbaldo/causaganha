"""DJEN proxy client — caderno info lookup and ZIP download."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from djen_backup.retry import request_with_retry

if TYPE_CHECKING:
    from datetime import date

    import httpx

log = structlog.get_logger()


class DJENNotFound(Exception):
    """Raised when the DJEN proxy returns 404 or an empty response."""

    def __init__(self, status_code: int, reason: str) -> None:
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

    Raises :class:`DJENNotFound` when the caderno is unavailable.
    """
    url = f"{base_url}/api/v1/caderno/{tribunal}/{d.isoformat()}/D"
    resp = await request_with_retry(client, "GET", url, retry_djen_400=True)

    if resp.status_code == 404:
        raise DJENNotFound(status_code=404, reason="Not Found")

    # Transient server errors (5xx, etc.) should propagate as HTTPStatusError
    # so the caller retries rather than permanently marking absent.
    resp.raise_for_status()

    try:
        data: dict[str, object] = resp.json()
    except ValueError as exc:
        raise DJENNotFound(status_code=resp.status_code, reason="Invalid JSON") from exc

    download_url = data.get("url")
    if not isinstance(download_url, str) or not download_url:
        raise DJENNotFound(status_code=resp.status_code, reason="Empty or missing URL field")

    return download_url


async def download_zip(
    client: httpx.AsyncClient,
    url: str,
) -> Path:
    """Download a ZIP file to a temporary file and return its path.

    The caller is responsible for cleaning up the temp file.
    Raises :class:`DJENNotFound` for 404 or empty responses.
    """
    resp = await request_with_retry(client, "GET", url)

    if resp.status_code == 404:
        raise DJENNotFound(status_code=404, reason="ZIP download 404")

    resp.raise_for_status()

    if len(resp.content) == 0:
        raise DJENNotFound(status_code=resp.status_code, reason="Empty ZIP response")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(resp.content)

    log.debug("zip_downloaded_to_file", path=tmp.name, size=len(resp.content))
    return Path(tmp.name)
