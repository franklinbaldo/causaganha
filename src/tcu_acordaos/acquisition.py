"""Safe acquisition helpers for official TCU Acórdãos bulk CSV files."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Callable
from urllib.parse import urlparse
from urllib.request import urlopen

_ALLOWED_HOST_SUFFIX = ".tcu.gov.br"
_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class DownloadEvidence:
    """Observed evidence for one downloaded official bulk artifact."""

    source_url: str
    final_url: str
    acquired_at: str
    size_bytes: int
    sha256: str


Opener = Callable[[str], BinaryIO]


def _validate_official_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        msg = "TCU bulk URL must use https"
        raise ValueError(msg)
    if host != "tcu.gov.br" and not host.endswith(_ALLOWED_HOST_SUFFIX):
        msg = "TCU bulk URL must be hosted on tcu.gov.br"
        raise ValueError(msg)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def download_official_csv(
    url: str,
    destination: Path,
    *,
    opener: Opener = urlopen,
    acquired_at: str | None = None,
) -> DownloadEvidence:
    """Download one official TCU CSV atomically and record byte-level evidence.

    The destination is replaced only after the complete response has been read. Redirects
    are accepted only when the final URL is still under ``tcu.gov.br``.
    """
    _validate_official_url(url)
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
            _validate_official_url(final_url)
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
