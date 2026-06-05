from __future__ import annotations


"""Shared Internet Archive S3-compatible upload utilities.

This is the canonical module for uploading files to Internet Archive
using the httpx-based S3-compatible API. All pipeline scripts should
import upload logic from here instead of defining their own.

CRITICAL: We use httpx (direct HTTP PUT) instead of boto3 or the
``internetarchive`` Python library. boto3 forces ``x-amz-meta-*`` headers
while IA requires ``x-archive-meta-*``. See CONTRIBUTING.md and PR #348.
"""


import configparser
import hashlib
import os
from pathlib import Path

import anyio
import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# Re-export the canonical CircuitBreaker so legacy callers
# (`from causaganha.pipeline.ia_s3 import CircuitBreaker`) keep working
# without duplicating the implementation. The class supports both sync
# (is_open / record_*) and async (allow_request) APIs.
from djen_backup.circuit_breaker import CircuitBreaker as CircuitBreaker  # noqa: PLC0414, TC001


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


def _is_retryable_upload_error(exception: Exception) -> bool:
    """Retry on network errors or retryable HTTP status codes."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in _RETRYABLE_STATUS_CODES
    return isinstance(exception, httpx.RequestError)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception(_is_retryable_upload_error),
    reraise=True,
)
async def _perform_upload(
    client: httpx.AsyncClient, url: str, file_path: Path, headers: dict[str, str]
) -> None:
    """Perform single upload attempt; retries are handled by tenacity."""
    content = await anyio.Path(file_path).read_bytes()
    response = await client.put(url, content=content, headers=headers)
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
