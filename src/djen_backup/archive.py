"""Internet Archive S3 upload and metadata queries.

The circuit-breaker class lives in ``djen_backup.circuit_breaker`` and is
re-exported here for backward compatibility with existing imports.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import httpx
import structlog
from aiolimiter import AsyncLimiter

from causaganha.pipeline import ia_s3
from djen_backup.circuit_breaker import CircuitBreaker, CircuitState
from djen_backup.retry import RETRIABLE_STATUS_CODES, _backoff, request_with_retry


__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "ItemBusyError",
    "check_ia_file_exists",
    "fetch_ia_existing",
    "get_ia_item_id",
    "get_ia_item_tribunal",
    "put_ia_bytes",
    "upload_zip",
]


if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

log = structlog.get_logger()

# ── HTTP status constants ────────────────────────────────────────────

HTTP_OK = 200
HTTP_NOT_FOUND = 404

# ── Per-item upload locks ────────────────────────────────────────────
#
# IA serializes writes per *item* (yearly bucket), not per access key.
# Two concurrent PUTs to the same item race; PUTs to different items
# are safe in parallel. We keep one lock per item_id so that distinct
# tribunal-year buckets upload in parallel while the same bucket stays
# serial.

_item_locks: dict[str, asyncio.Lock] = {}
_item_locks_guard = asyncio.Lock()

# Rate limit: ~1.5 uploads / s steady-state, burst of 12.
# aiolimiter's leaky bucket: max_rate uploads per time_period.
_IA_RATE_LIMITER = AsyncLimiter(max_rate=12, time_period=8)


async def _lock_for(item_id: str) -> asyncio.Lock:
    """Return (creating if necessary) the per-item asyncio.Lock."""
    async with _item_locks_guard:
        lock = _item_locks.get(item_id)
        if lock is None:
            lock = asyncio.Lock()
            _item_locks[item_id] = lock
        return lock


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


# ── Item naming helpers ───────────────────────────────────────────────


def get_ia_item_id(tribunal: str, d: date) -> str:
    """Canonical item naming strategy: djen-{tribunal}-{year}."""
    return f"djen-{tribunal.lower()}-{d.year}"


def get_ia_item_tribunal(item_id: str) -> str:
    """Extract the tribunal code from ``djen-{tribunal}-{year}`` item ids."""
    prefix = "djen-"
    if not item_id.startswith(prefix):
        msg = f"Invalid IA item id: {item_id!r}"
        raise ValueError(msg)

    body = item_id[len(prefix) :]
    tribunal, sep, year = body.rpartition("-")
    if not sep or not tribunal or not year.isdigit():
        msg = f"Invalid IA item id: {item_id!r}"
        raise ValueError(msg)
    return tribunal.upper()


# ── IA existence check ───────────────────────────────────────────────


async def check_ia_file_exists(
    client: httpx.AsyncClient,
    tribunal: str,
    d: date,
) -> bool:
    """HEAD-check whether a ZIP already exists on IA for this tribunal+date."""
    item_id = get_ia_item_id(tribunal, d)
    filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
    url = f"https://archive.org/download/{item_id}/{filename}"
    try:
        resp = await client.head(url)
    except (httpx.HTTPError, httpx.RequestError):
        return False
    else:
        return resp.status_code == HTTP_OK


# ── IA S3 upload ─────────────────────────────────────────────────────


async def put_ia_bytes(
    client: httpx.AsyncClient,
    url: str,
    content: bytes,
    headers: dict[str, str],
    *,
    max_retries: int = 7,
) -> httpx.Response:
    """Upload bytes to IA S3 with retry policy.

    Used for small JSON state files (no rate-limiting needed).
    For ZIP uploads use :func:`upload_zip` instead.
    """
    last_resp: httpx.Response | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.request("PUT", url, content=content, headers=headers)
            last_resp = resp
            if resp.status_code == HTTP_OK or resp.status_code not in RETRIABLE_STATUS_CODES:
                break
        except (httpx.TransportError, httpx.TimeoutException):
            wait = max(5.0, float(2**attempt))
            if attempt < max_retries:
                await asyncio.sleep(wait)
                continue
            raise

        if attempt < max_retries:
            body_text = resp.text[:200] if resp.text else "No body"
            if "SlowDown" in body_text or "bucket_tasks_queued" in body_text:
                log.warning("upload_bucket_saturated", status=resp.status_code, url=url)
                return resp

            wait = _backoff(attempt, resp)
            await asyncio.sleep(wait)
            continue
        break

    assert last_resp is not None
    return last_resp


class ItemBusyError(Exception):
    """Raised when the target IA item is currently locked by another worker."""


async def upload_zip(
    client: httpx.AsyncClient,
    item_id: str,
    zip_path: Path,
    *,
    circuit_breaker: CircuitBreaker | None = None,
    try_lock: bool = False,
) -> bool:
    """Upload a ZIP file to IA S3.

    Applies a per-item lock (serialises PUTs to the same yearly bucket)
    and the global token-bucket rate limiter (respects IA's write rate).

    When ``try_lock=True``, raises :class:`ItemBusyError` if the item
    lock is held — caller can re-queue and process another item instead
    of blocking.

    Returns ``True`` on success, ``False`` on failure or open circuit.
    """
    if circuit_breaker is not None and not await circuit_breaker.allow_request():
        log.warning("upload_skipped_circuit_open", item_id=item_id)
        return False

    # Extract date string from filename: djen-YYYY-MM-DD-TRIBUNAL.zip
    stem_parts = zip_path.stem.split("-")
    date_str = f"{stem_parts[1]}-{stem_parts[2]}-{stem_parts[3]}" if len(stem_parts) >= 4 else ""  # noqa: PLR2004

    lock = await _lock_for(item_id)
    if try_lock and lock.locked():
        raise ItemBusyError(item_id)
    async with lock:
        await _IA_RATE_LIMITER.acquire()  # aiolimiter supports .acquire() or async with
        start = time.monotonic()
        log.info("upload_starting", item_id=item_id, file=zip_path.name)
        try:
            ok = await ia_s3.upload_to_ia(client, item_id, zip_path, date_str)
        except Exception as exc:
            elapsed = round(time.monotonic() - start, 1)
            log.exception(
                "upload_exception",
                item_id=item_id,
                file=zip_path.name,
                elapsed_s=elapsed,
                error=str(exc),
            )
            if circuit_breaker is not None:
                circuit_breaker.record_failure()
            return False

    elapsed = round(time.monotonic() - start, 1)
    if ok:
        log.info("upload_complete", item_id=item_id, file=zip_path.name, elapsed_s=elapsed)
        if circuit_breaker is not None:
            circuit_breaker.record_success()
    else:
        log.warning("upload_failed", item_id=item_id, file=zip_path.name, elapsed_s=elapsed)
        if circuit_breaker is not None:
            circuit_breaker.record_failure()
    return ok


# Circuit breaker class lives in djen_backup.circuit_breaker (imported above).
