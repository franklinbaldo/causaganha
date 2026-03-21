"""Shared Internet Archive S3-compatible upload utilities.

This is the canonical module for uploading files to Internet Archive
using the httpx-based S3-compatible API. All pipeline scripts should
import upload logic from here instead of defining their own.

CRITICAL: We use httpx (direct HTTP PUT) instead of boto3 or the
``internetarchive`` Python library. boto3 forces ``x-amz-meta-*`` headers
while IA requires ``x-archive-meta-*``. See CONTRIBUTING.md and PR #348.
"""

from __future__ import annotations

import configparser
import hashlib
import os
from pathlib import Path

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


logger = structlog.get_logger()

_IA_S3_URL = "https://s3.us.archive.org"


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
# Circuit breaker (optional, for resilience during IA outages)
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Lightweight circuit breaker for IA upload operations.

    After *threshold* consecutive failures the breaker opens and
    ``is_open`` returns ``True``, allowing callers to skip further
    attempts and avoid wasting requests during an IA outage.
    """

    def __init__(self, threshold: int = 5) -> None:
        self.consecutive_failures = 0
        self.threshold = threshold

    def record_success(self) -> None:
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    @property
    def is_open(self) -> bool:
        return self.consecutive_failures >= self.threshold


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def create_upload_client(
    auth: str,
    timeout: int = 300,
    max_connections: int = 10,
) -> httpx.Client:
    """Create a properly configured httpx client WITH auth headers.

    Args:
        auth: ``"LOW access:secret"`` authorization string.
        timeout: Request timeout in seconds.
        max_connections: Connection pool size.

    Returns:
        An ``httpx.Client`` ready for IA S3 PUT requests.
    """
    return httpx.Client(
        timeout=timeout,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        ),
        headers={"Authorization": auth},
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def _is_retryable_upload_error(exception: Exception) -> bool:
    """Retry on network errors or 5xx server errors."""
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500
    return isinstance(exception, httpx.RequestError)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable_upload_error),
    reraise=True,
)
def _perform_upload(
    client: httpx.Client, url: str, file_path: Path, headers: dict[str, str]
) -> None:
    """Perform single upload attempt with no internal retry logic (handled by tenacity)."""
    with file_path.open("rb") as f:
        response = client.put(url, content=f, headers=headers)
    response.raise_for_status()


def upload_to_ia(
    client: httpx.Client,
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
        item_id: IA item identifier (e.g. ``"djen-2026-01-27"``).
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

    headers: dict[str, str] = {
        "Content-MD5": content_md5,
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        "x-archive-meta-collection": "opensource",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-title": f"DJEN Data - {date_str}",
        "x-archive-meta-description": (
            "Diario de Justica Eletronico Nacional - Judicial communications from Brazilian courts."
        ),
        "x-archive-meta-subject": "brazilian-law;djen;legal;judiciary;open-data",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-date": date_str,
    }

    # Apply caller-supplied overrides (e.g. consolidate uses different title)
    if metadata_overrides:
        headers.update(metadata_overrides)

    try:
        _perform_upload(client, url, file_path, headers)
        if circuit_breaker is not None:
            circuit_breaker.record_success()
    except Exception as e:
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
