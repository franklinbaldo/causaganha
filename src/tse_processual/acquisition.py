"""Safe acquisition of official TSE Processual ZIP artifacts."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Callable
from urllib.parse import urlparse

import httpx

from common.relay import relay_transport_from_env

_ALLOWED_HOST = "cdn.tse.jus.br"
_CHUNK_SIZE = 1024 * 1024


class InvalidOfficialUrlError(ValueError):
    """Raised when a URL escapes the admitted TSE Processual boundary."""

    _MESSAGES = {
        "scheme": "TSE Processual URL must use https",
        "host": "TSE Processual URL must be hosted on cdn.tse.jus.br",
        "path": "TSE Processual URL must remain under the official processual path",
    }

    def __init__(self, reason: str) -> None:
        super().__init__(self._MESSAGES[reason])


@dataclass(frozen=True, slots=True)
class DownloadEvidence:
    """Byte-level provenance observed while acquiring one official resource."""

    source_url: str
    final_url: str
    acquired_at: str
    size_bytes: int
    sha256: str


Opener = Callable[[str], BinaryIO]


def _make_client() -> httpx.Client:
    """Configured client for official TSE downloads.

    Routes through the relay (see ``common.relay``) when ``RELAY_URL``/
    ``RELAY_TOKEN`` are set — issue #985: TSE's Akamai front 403s every
    path from this sandbox's egress, the same WAF-block class the relay
    bypasses for STJ/TJRO. Direct connection otherwise (local/dev default).
    """
    return httpx.Client(timeout=120, follow_redirects=True, transport=relay_transport_from_env())


_CLIENT = _make_client()


class _StreamingResponse:
    """Adapts an httpx streaming response to the ``urlopen``-style Opener contract."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self._iterator = response.iter_bytes(_CHUNK_SIZE)

    def geturl(self) -> str:
        """Return the true final URL — the real destination, even when relayed."""
        return str(self._response.url)

    def read(self, _size: int = _CHUNK_SIZE) -> bytes:
        """Return the next chunk, or ``b""`` once the response is exhausted."""
        return next(self._iterator, b"")

    def __enter__(self) -> _StreamingResponse:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self._response.close()


def _default_opener(url: str) -> _StreamingResponse:
    """Default Opener: GET via ``_CLIENT``, transparently relayed when configured."""
    request = _CLIENT.build_request("GET", url)
    response = _CLIENT.send(request, stream=True)
    response.raise_for_status()
    return _StreamingResponse(response)


def validate_official_url(url: str) -> None:
    """Reject non-HTTPS and non-TSE CDN URLs."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise InvalidOfficialUrlError("scheme")
    if (parsed.hostname or "").lower() != _ALLOWED_HOST:
        raise InvalidOfficialUrlError("host")
    if not parsed.path.startswith("/estatistica/sead/odsele/processual/"):
        raise InvalidOfficialUrlError("path")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def download_official_zip(
    url: str,
    destination: Path,
    *,
    opener: Opener = _default_opener,
    acquired_at: str | None = None,
) -> DownloadEvidence:
    """Download one official ZIP atomically and record size/checksum provenance."""
    validate_official_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    replaced = False
    try:
        with os.fdopen(fd, "wb") as output, opener(url) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            validate_official_url(final_url)
            while chunk := response.read(_CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(destination)
        replaced = True
    finally:
        if not replaced:
            temporary.unlink(missing_ok=True)

    return DownloadEvidence(
        source_url=url,
        final_url=final_url,
        acquired_at=acquired_at or _utc_now(),
        size_bytes=size,
        sha256=digest.hexdigest(),
    )
