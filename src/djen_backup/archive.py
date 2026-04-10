"""Internet Archive S3 upload, metadata queries, and circuit breaker."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from enum import StrEnum
from typing import TYPE_CHECKING

import httpx
import structlog

from djen_backup.retry import RETRIABLE_STATUS_CODES, _backoff, request_with_retry


if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from djen_backup.engine import SyncObserver

log = structlog.get_logger()

# ── HTTP status constants ────────────────────────────────────────────

HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_SERVICE_UNAVAILABLE = 503

# ── IA metadata ──────────────────────────────────────────────────────


async def fetch_ia_existing(
    client: httpx.AsyncClient,
    tribunal: str,
    year: int,
) -> dict[date, str]:
    """Query IA metadata for a tribunal+year; return ``{date: "uploaded"}``.

    Queries the bucket djen-{tribunal}-{year}.
    """
    from datetime import date

    item_id = get_ia_item_id(tribunal, date(year, 1, 1))
    url = f"https://archive.org/metadata/{item_id}/files"
    resp = await request_with_retry(client, "GET", url)
    if resp.status_code != HTTP_OK:
        if resp.status_code != HTTP_NOT_FOUND:
            log.warning("ia_metadata_error", item_id=item_id, status=resp.status_code)
        return {}

    try:
        data: dict[str, object] = resp.json()
    except ValueError:
        return {}

    result: dict[date, str] = {}
    files = data.get("result")
    if not isinstance(files, list):
        return result

    # Filename format: djen-YYYY-MM-DD-TRIBUNAL.zip
    # We look for files starting with djen- and ending with .zip
    for entry in files:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        if name.startswith("djen-") and name.endswith(".zip"):
            parts = name[len("djen-") : -len(".zip")].split("-")
            # Expected parts: [YYYY, MM, DD, TRIBUNAL]
            if len(parts) >= 3:
                try:
                    d = date.fromisoformat(f"{parts[0]}-{parts[1]}-{parts[2]}")
                    result[d] = "uploaded"
                except ValueError:
                    continue

    return result


# ── IA S3 upload ─────────────────────────────────────────────────────

IA_S3_URL = "https://s3.us.archive.org/{item}/{filename}"

# Module-level upload lock: IA rate-limits to ~1 upload/second per access key.
# This lock serializes uploads across all workers; downloads from DJEN run in parallel.
_upload_lock = asyncio.Lock()
_UPLOAD_COOLDOWN_S = 5.0


def get_ia_item_id(tribunal: str, d: date) -> str:
    """Canonical item naming strategy: djen-{tribunal}-{year}."""
    return f"djen-{tribunal.lower()}-{d.year}"


def _content_md5(data: bytes) -> str:
    """Return base64-encoded MD5 digest per the S3 Content-MD5 spec."""
    digest = hashlib.md5(data, usedforsecurity=False).digest()
    return base64.b64encode(digest).decode("ascii")


def _build_upload_headers(
    d: date,
    content_md5: str,
    content_type: str,
    auth: str,
) -> dict[str, str]:
    return {
        "Authorization": auth,
        "Content-MD5": content_md5,
        "Content-Type": content_type,
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-collection": "opensource",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-subject": "brazilian-law;djen;legal;judiciary",
    }


async def upload_zip(
    client: httpx.AsyncClient,
    d: date,
    tribunal: str,
    zip_path: Path,
    auth: str,
    observer: SyncObserver | None = None,
) -> httpx.Response:
    """Upload a ZIP file to IA S3 with fine-grained locking and retries.

    Releases the global upload lock during retry backoff periods to prevent
    blocking the entire queue when one item is rate-limited.
    """
    start_time = time.monotonic()
    content = await asyncio.to_thread(zip_path.read_bytes)
    size_mb = round(len(content) / 1024 / 1024, 1)
    filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
    item_id = get_ia_item_id(tribunal, d)
    url = IA_S3_URL.format(item=item_id, filename=filename)
    md5 = _content_md5(content)
    headers = _build_upload_headers(d, md5, "application/zip", auth)

    log.info("upload_starting", date=d.isoformat(), tribunal=tribunal, size_mb=size_mb)

    max_retries = 7
    last_resp: httpx.Response | None = None

    for attempt in range(max_retries + 1):
        try:
            async with _upload_lock:
                resp = await client.request("PUT", url, content=content, headers=headers)
                last_resp = resp
                # If success or non-retriable, we still hold the lock for the cooldown
                if resp.status_code == HTTP_OK or resp.status_code not in RETRIABLE_STATUS_CODES:
                    await asyncio.sleep(_UPLOAD_COOLDOWN_S)
                    break
        except (httpx.TransportError, httpx.TimeoutException):
            wait = max(5.0, float(2**attempt))
            if attempt < max_retries:
                if observer:
                    observer.on_retry(tribunal, d, attempt + 1, 0, wait, body="Transport/Timeout")
                await asyncio.sleep(wait)
                continue
            raise

        if attempt < max_retries:
            body_text = resp.text[:200] if resp.text else "No body"

            # If the error is a specific "Slow Down" or "Bucket Queued" from IA,
            # we don't just wait; we return so the engine can switch to a different tribunal.
            if "SlowDown" in body_text or "bucket_tasks_queued" in body_text:
                log.warning("upload_bucket_saturated", tribunal=tribunal, status=resp.status_code)
                if observer:
                    observer.on_retry(
                        tribunal,
                        d,
                        attempt + 1,
                        resp.status_code,
                        0,
                        body="Bucket Saturated - Switching",
                    )
                return resp

            wait = _backoff(attempt, resp)
            if observer:
                observer.on_retry(tribunal, d, attempt + 1, resp.status_code, wait, body=body_text)
            await asyncio.sleep(wait)
            continue
        break

    assert last_resp is not None
    elapsed = round(time.monotonic() - start_time, 1)
    body = last_resp.content or b""
    if last_resp.status_code == HTTP_OK:
        log.info(
            "upload_complete",
            date=d.isoformat(),
            tribunal=tribunal,
            size_mb=size_mb,
            elapsed_s=elapsed,
        )
    else:
        body_preview = body[:500].decode("utf-8", errors="replace") if body else "<empty>"
        if b"appears to be spam" in body:
            log.warning(
                "upload_spam_rejected",
                date=d.isoformat(),
                tribunal=tribunal,
                status=last_resp.status_code,
                body=body_preview,
            )
        else:
            log.error(
                "upload_failed",
                date=d.isoformat(),
                tribunal=tribunal,
                status=last_resp.status_code,
                elapsed_s=elapsed,
                body=body_preview,
            )
    return last_resp


# ── Circuit breaker ──────────────────────────────────────────────────


class CircuitState(StrEnum):
    """States for the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker with half-open recovery for IA uploads.

    - CLOSED: normal operation, count consecutive failures.
    - OPEN: after *threshold* failures, refuse requests for *recovery_timeout* seconds.
    - HALF_OPEN: after timeout elapses, allow **one** test request.
      Success → CLOSED.  Failure → OPEN with doubled timeout (capped at 5 min).
    """

    def __init__(
        self,
        threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        """Initialize the circuit breaker with failure threshold and recovery timeout."""
        self._threshold = threshold
        self._base_recovery = recovery_timeout
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the current state (for external inspection / tests)."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._opened_at >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    def _state_locked(self) -> CircuitState:
        """Compute state while the lock is held (avoids TOCTOU)."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._opened_at >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def allow_request(self) -> bool:
        """Check if a request is allowed by the circuit breaker."""
        async with self._lock:
            s = self._state_locked()
            if s == CircuitState.CLOSED:
                return True
            if s == CircuitState.HALF_OPEN:
                # Consume the probe slot — transition to OPEN so only one
                # worker gets through while the test request is in-flight.
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                return True
            return False

    async def record_success(self) -> None:
        """Record a successful request and reset the circuit."""
        async with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._recovery_timeout = self._base_recovery

    async def record_failure(self) -> None:
        """Record a failed request and update circuit state accordingly."""
        async with self._lock:
            self._failure_count += 1
            if self._state_locked() == CircuitState.HALF_OPEN:
                # Test request failed — reopen with increased timeout
                self._recovery_timeout = min(self._recovery_timeout * 2, 300.0)
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                log.warning(
                    "circuit_breaker_reopen",
                    next_retry_s=self._recovery_timeout,
                )
            elif self._failure_count >= self._threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                log.error(
                    "circuit_breaker_open",
                    failures=self._failure_count,
                    recovery_s=self._recovery_timeout,
                )
