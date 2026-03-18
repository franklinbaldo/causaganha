"""Internet Archive S3 upload, metadata queries, and circuit breaker."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

import structlog

from djen_backup.retry import request_with_retry


if TYPE_CHECKING:
    from pathlib import Path

    import httpx

log = structlog.get_logger()

# ── IA metadata ──────────────────────────────────────────────────────

IA_METADATA_URL = "https://archive.org/metadata/backup-djen-{date}"


async def fetch_ia_existing(
    client: httpx.AsyncClient,
    d: date,
) -> dict[str, str]:
    """Query IA metadata; return ``{tribunal: "uploaded"|"absent"}``."""
    url = IA_METADATA_URL.format(date=d.isoformat())
    resp = await request_with_retry(client, "GET", url)
    if resp.status_code != 200:
        log.warning("ia_metadata_error", date=d.isoformat(), status=resp.status_code)
        return {}

    try:
        data: dict[str, object] = resp.json()
    except ValueError:
        return {}

    result: dict[str, str] = {}
    files = data.get("files")
    if not isinstance(files, list):
        return result

    prefix = f"backup-djen-{d.isoformat()}-"
    for entry in files:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.startswith(prefix):
            continue
        rest = name[len(prefix) :]
        if rest.endswith(".zip"):
            result[rest[: -len(".zip")]] = "uploaded"
        elif rest.endswith(".absent"):
            result[rest[: -len(".absent")]] = "absent"
    return result


# ── IA S3 upload ─────────────────────────────────────────────────────

IA_S3_URL = "https://s3.us.archive.org/backup-djen-{date}/{filename}"


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
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        "x-archive-meta-collection": "opensource",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-title": f"DJEN Data - {d.isoformat()}",
        "x-archive-meta-description": (
            "Diario de Justica Eletronico Nacional - Judicial communications from Brazilian courts."
        ),
        "x-archive-meta-subject": "brazilian-law;djen;legal;judiciary;open-data",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-date": d.isoformat(),
    }


async def upload_zip(
    client: httpx.AsyncClient,
    d: date,
    tribunal: str,
    zip_path: Path,
    auth: str,
) -> httpx.Response:
    """Upload a ZIP file to IA S3.

    Reads *zip_path* into memory for the upload.
    """
    content = zip_path.read_bytes()
    filename = f"djen-{d.isoformat()}-{tribunal}.zip"
    url = IA_S3_URL.format(date=d.isoformat(), filename=filename)
    md5 = _content_md5(content)
    headers = _build_upload_headers(d, md5, "application/zip", auth)

    log.info("ia_upload_start", date=d.isoformat(), tribunal=tribunal, size=len(content))
    resp = await request_with_retry(
        client,
        "PUT",
        url,
        content=content,
        headers=headers,
    )
    body = resp.content or b""
    if resp.status_code == 200:
        log.info(
            "ia_upload_done",
            date=d.isoformat(),
            tribunal=tribunal,
            status=resp.status_code,
        )
    else:
        body_preview = body[:500].decode("utf-8", errors="replace") if body else "<empty>"
        if b"appears to be spam" in body:
            log.warning(
                "ia_upload_spam_rejected",
                date=d.isoformat(),
                tribunal=tribunal,
                status=resp.status_code,
                body=body_preview,
            )
        else:
            log.error(
                "ia_upload_failed",
                date=d.isoformat(),
                tribunal=tribunal,
                status=resp.status_code,
                body=body_preview,
            )
    return resp


async def upload_absent_marker(
    client: httpx.AsyncClient,
    d: date,
    tribunal: str,
    status_code: int,
    reason: str,
    auth: str,
) -> httpx.Response:
    """Upload a ``.absent`` marker with metadata JSON."""
    import json

    filename = f"djen-{d.isoformat()}-{tribunal}.absent"
    url = IA_S3_URL.format(date=d.isoformat(), filename=filename)

    body = json.dumps(
        {
            "status_code": status_code,
            "reason": reason,
            "checked_at": datetime.now(tz=UTC).isoformat(),
        }
    ).encode()

    md5 = _content_md5(body)
    headers = _build_upload_headers(d, md5, "application/json", auth)

    log.info("ia_absent_marker", date=d.isoformat(), tribunal=tribunal)
    return await request_with_retry(
        client,
        "PUT",
        url,
        content=body,
        headers=headers,
    )


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
