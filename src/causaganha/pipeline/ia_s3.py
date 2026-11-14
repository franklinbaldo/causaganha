from __future__ import annotations

import configparser
import hashlib
import os
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

import anyio
import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# Re-export the canonical CircuitBreaker so legacy callers
# (`from causaganha.pipeline.ia_s3 import CircuitBreaker`) keep working
# without duplicating the implementation. The class supports both sync
# (is_open / record_*) and async (allow_request) APIs.
from djen_backup.circuit_breaker import CircuitBreaker as CircuitBreaker  # noqa: PLC0414, TC001

"""Shared Internet Archive S3-compatible upload utilities.

This is the canonical module for uploading files to Internet Archive
using the httpx-based S3-compatible API. All pipeline scripts should
import upload logic from here instead of defining their own.

CRITICAL: We use httpx (direct HTTP PUT) instead of boto3 or the
``internetarchive`` Python library. boto3 forces ``x-amz-meta-*`` headers
while IA requires ``x-archive-meta-*``. See CONTRIBUTING.md and PR #348.
"""


logger = structlog.get_logger()

HTTP_500_INTERNAL_SERVER_ERROR = 500
_IA_S3_URL = "https://s3.us.archive.org"

# Status codes worth retrying:
#   408 = request timeout, 429 = rate limit
#   500/502/503/504 = transient server errors (503 most common on IA during item lock,
#   502 Bad Gateway from IA's edge layer is also transient)
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


def get_ia_s3_auth() -> str | None:
    """Resolve IA S3 authorization header value from env vars or config file.

    Checks (in order):
        1. ``IAS3_ACCESS_KEY`` / ``IAS3_SECRET_KEY`` environment variables
        2. ``~/.config/internetarchive/ia.ini`` ``[s3]`` section

    Returns:
        ``"LOW access:secret"`` string suitable for an ``Authorization`` header,
        or *None* when no credentials are found.
    """
    access = os.environ.get("IAS3_ACCESS_KEY", "")
    secret = os.environ.get("IAS3_SECRET_KEY", "")
    if access and secret:
        return f"LOW {access}:{secret}"
    # Fall back to config file (created by CI workflow or `ia configure`)
    config_path = Path.home() / ".config" / "internetarchive" / "ia.ini"
    if config_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        access = cfg.get("s3", "access", fallback="")
        secret = cfg.get("s3", "secret", fallback="")
        if access and secret:
            return f"LOW {access}:{secret}"
    return None


# ---------------------------------------------------------------------------
# Metadata header encoding
# ---------------------------------------------------------------------------


def meta_value(value: str) -> str:
    """Encode an IA ``x-archive-meta-*`` header value.

    HTTP header values must be ASCII (httpx raises ``UnicodeEncodeError``
    otherwise). IA's S3 API accepts non-ASCII metadata via its
    ``uri(<percent-encoded>)`` convention — the same one used by the
    official ``internetarchive`` library.
    """
    if value.isascii():
        return value
    return f"uri({quote(value, safe='')})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_ia_item_id(tribunal: str, date_str: str) -> str:
    """Canonical item naming strategy: djen-{tribunal}-{year}.

    Args:
        tribunal: Tribunal code (e.g. TJSP, TRE-AC).
        date_str: Date string (YYYY-MM-DD or datetime object with isoformat).

    Returns:
        The canonical item ID for the Internet Archive.
    """
    year = date_str[:4]
    return f"djen-{tribunal.lower()}-{year}"


def compute_md5(file_path: Path) -> str:
    """Compute hex-encoded MD5 checksum (IA S3 format)."""
    h = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_deadline(duration_str: str) -> int:
    """Parse a deadline string (e.g. ``'10m'``, ``'600s'``) into seconds."""
    if not duration_str:
        return 0
    duration_str = duration_str.strip().lower()
    try:
        if duration_str.endswith("m"):
            return int(float(duration_str[:-1]) * 60)
        if duration_str.endswith("s"):
            return int(float(duration_str[:-1]))
        return int(float(duration_str))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def create_upload_client(
    auth: str,
    timeout: int = 300,
    max_connections: int = 25,
) -> httpx.AsyncClient:
    """Create a properly configured async httpx client WITH auth headers.

    The returned client supports ``async with`` and should be used as an
    async context manager so connections are properly closed.

    Args:
        auth: ``"LOW access:secret"`` authorization string.
        timeout: Request timeout in seconds.
        max_connections: Connection pool size. Default 25 saturates most
            uplinks without triggering IA 503 rate-limiting.

    Returns:
        An ``httpx.AsyncClient`` ready for IA S3 PUT requests.
    """
    return httpx.AsyncClient(
        timeout=timeout,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        ),
        headers={"Authorization": auth},
        # IA S3 occasionally issues 307 redirects; follow them automatically.
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


#: Chunk size for streaming a local file into an upload body. Peak memory per
#: in-flight upload is one chunk, not the whole file (consolidate partitions
#: are 2-3 GB parquet files).
_UPLOAD_CHUNK_BYTES = 16 * 1024 * 1024

# OSErrors that are deterministic for this file/attempt and will not clear on
# retry. Any other OSError raised mid-transfer (connection reset, broken pipe,
# transient I/O error reading the local file) is treated as transient.
_NON_TRANSIENT_OS_ERRORS = (FileNotFoundError, PermissionError, IsADirectoryError)


def _is_retryable_upload_error(exception: Exception) -> bool:
    """Retry on network errors, retryable HTTP status codes, or transient OSError.

    A mid-transfer ``OSError`` (e.g. ``ConnectionResetError``, or an
    ``[Errno 0] Error`` surfacing from the socket or the local read while the
    body is streaming) is not wrapped by httpx, so it must be matched here
    explicitly or the upload is abandoned after a single attempt.
    """
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in _RETRYABLE_STATUS_CODES
    if isinstance(exception, httpx.RequestError):
        return True
    return isinstance(exception, OSError) and not isinstance(exception, _NON_TRANSIENT_OS_ERRORS)


class _FileChunkStream:
    """Re-iterable async request body that streams a local file in chunks.

    httpx replays a redirected body only if it is not a generator: an async
    generator body raises ``StreamConsumed`` on a 307/308 (IA occasionally
    issues these). So this is a plain object whose ``__aiter__`` opens the
    file afresh on every iteration. The file is re-read from the start each
    time, which keeps retries and redirects sending the full body.
    """

    def __init__(self, file_path: Path, size: int) -> None:
        self._path = file_path
        self._size = size

    async def __aiter__(self) -> AsyncIterator[bytes]:
        sent = 0
        async with await anyio.Path(self._path).open("rb") as fh:
            while chunk := await fh.read(_UPLOAD_CHUNK_BYTES):
                sent += len(chunk)
                yield chunk
        if sent != self._size:
            message = (
                f"{self._path.name} changed size during upload (stat={self._size}, read={sent})"
            )
            raise OSError(message)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception(_is_retryable_upload_error),
    reraise=True,
)
async def _perform_upload(
    client: httpx.AsyncClient, url: str, file_path: Path, headers: dict[str, str]
) -> None:
    """Perform single upload attempt; retries are handled by tenacity.

    The body is streamed from disk. Size is stat'ed per attempt and sent as an
    explicit ``Content-Length`` (IA S3 requires a length; without it httpx
    would use chunked transfer encoding).
    """
    size = (await anyio.Path(file_path).stat()).st_size
    body = _FileChunkStream(file_path, size)
    response = await client.put(
        url,
        content=body,
        headers={**headers, "Content-Length": str(size)},
    )
    response.raise_for_status()


async def upload_to_ia(
    client: httpx.AsyncClient,
    item_id: str,
    file_path: Path,
    date_str: str,
    metadata_overrides: dict[str, str] | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> bool:
    """Upload a file to Internet Archive via the S3-compatible API.

    CRITICAL: We use httpx (direct HTTP PUT) instead of boto3.
    boto3 forces ``x-amz-meta-*`` headers while IA requires
    ``x-archive-meta-*``. See CONTRIBUTING.md and PR #348.

    Args:
        client: Shared httpx client (should have Authorization header).
        item_id: IA item identifier (e.g. ``"djen-tjro-2025"``).
        file_path: Local file to upload.
        date_str: Date string for metadata (``YYYY-MM-DD``).
        metadata_overrides: Optional dict of ``x-archive-meta-*`` values
            to override the defaults (e.g. title, description).
        circuit_breaker: Optional :class:`CircuitBreaker` instance.
            When the breaker is open the upload is skipped.

    Returns:
        ``True`` on success, ``False`` on failure or circuit-breaker trip.
    """
    if circuit_breaker is not None and circuit_breaker.is_open:
        logger.warning("circuit_breaker_open", item_id=item_id, file=file_path.name)
        return False

    filename = file_path.name
    url = f"{_IA_S3_URL}/{item_id}/{filename}"
    content_md5 = compute_md5(file_path)

    # Extract tribunal code from item_id for enriched metadata
    tribunal_code = ""
    parts = item_id.split("-")
    is_yearly = False
    if len(parts) >= 3 and parts[0] == "djen":
        if len(parts[-1]) == 4 and parts[-1].isdigit():
            is_yearly = True
        # Handle "djen-tjsp-2026" and "djen-tre-ac-2026"
        tribunal_code = "-".join(parts[1:-1]).upper()

    # Determine better title/description
    if is_yearly:
        title = f"DJEN {tribunal_code} - {parts[-1]} (Daily ZIP Archives)"
        description = (
            f"Annual archive of official judicial communications from the {tribunal_code} "
            f"tribunal for the year {parts[-1]}. This item contains raw daily ZIP files "
            "archived by CausaGanha to ensure permanent public access to Brazilian court data."
        )
    else:
        title = f"DJEN {tribunal_code} - {date_str}" if tribunal_code else f"DJEN Data - {date_str}"
        description = (
            f"Diario de Justica Eletronico Nacional ({tribunal_code}) - "
            "Judicial communications from Brazilian courts. "
            "Public domain data archived by CausaGanha. "
            "Query with DuckDB: SELECT * FROM read_parquet('https://archive.org/download/"
            f"{item_id}/comunicacoes.parquet')"
        )

    headers: dict[str, str] = {
        "Content-MD5": content_md5,
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        # Collection: defaults to "opensource". Set IA_COLLECTION env var to use
        # a custom collection (e.g. "causaganha") once created on archive.org.
        "x-archive-meta-collection": os.environ.get("IA_COLLECTION", "opensource"),
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-title": title,
        "x-archive-meta-description": description,
        "x-archive-meta-subject": f"brazilian-law;djen;legal;judiciary;open-data;{tribunal_code.lower()};causaganha;"
        f"{tribunal_code.lower()}-{parts[-1] if is_yearly else date_str[:4]}",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-date": date_str if not is_yearly else parts[-1],
        "x-archive-meta-language": "por",
        "x-archive-meta-licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        "x-archive-meta-source": "https://www.cnj.jus.br/tecnologia-da-informacao-e-comunicacao/djen/",
    }

    # Apply caller-supplied overrides (e.g. consolidate uses different title)
    if metadata_overrides:
        headers.update(metadata_overrides)

    try:
        await _perform_upload(client, url, file_path, headers)
        if circuit_breaker is not None:
            circuit_breaker.record_success()
    except (httpx.HTTPError, httpx.RequestError, OSError) as e:
        logger.warning(
            "upload_failed",
            item_id=item_id,
            file=filename,
            error=str(e),
        )
        if circuit_breaker is not None:
            circuit_breaker.record_failure()
        return False
    else:
        return True
