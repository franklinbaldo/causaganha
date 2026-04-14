"""HTTP request retry logic using tenacity."""

from __future__ import annotations

import httpx
import structlog
import tenacity


log = structlog.get_logger()

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_SERVICE_UNAVAILABLE = 503

RETRIABLE_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


def _retriable_response(
    resp: httpx.Response,
    *,
    retry_djen_400: bool,
    retry_404: bool,
) -> bool:
    """Predicate for tenacity ``retry_if_result``."""
    if resp.status_code in RETRIABLE_STATUS_CODES:
        return True
    if retry_djen_400 and resp.status_code == HTTP_BAD_REQUEST:
        return True
    return bool(retry_404 and resp.status_code == HTTP_NOT_FOUND)


def _wait(retry_state: tenacity.RetryCallState) -> float:
    """Respect ``Retry-After`` header when present, else exponential backoff.

    503 responses get a 15s minimum (IA bucket creation is slow).
    """
    outcome = retry_state.outcome
    base = float(2**retry_state.attempt_number)
    if outcome is None or outcome.failed:
        return base
    resp: httpx.Response = outcome.result()
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    if resp.status_code == HTTP_SERVICE_UNAVAILABLE:
        return max(base, 15.0)
    return base


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 7,
    retry_djen_400: bool = False,
    retry_404: bool = False,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Send an HTTP request with retries and exponential backoff.

    Retriable conditions:
    - Network / transport errors (``httpx.TransportError``, ``TimeoutException``)
    - Status codes: 408, 429, 500, 502, 503, 504
    - DJEN proxy 400 (transient) when ``retry_djen_400=True``
    - 404 when ``retry_404=True``

    Respects ``Retry-After`` header when present.
    """
    async for attempt in tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(max_retries + 1),
        wait=_wait,
        retry=(
            tenacity.retry_if_exception_type((httpx.TransportError, httpx.TimeoutException))
            | tenacity.retry_if_result(
                lambda r: _retriable_response(
                    r, retry_djen_400=retry_djen_400, retry_404=retry_404
                )
            )
        ),
        reraise=True,
    ):
        with attempt:
            return await client.request(method, url, content=content, headers=headers)
    # Unreachable — tenacity either returns via attempt or raises.
    msg = "unreachable"
    raise RuntimeError(msg)  # pragma: no cover


def _backoff(attempt: int, resp: httpx.Response) -> float:
    """Backwards-compat helper (used by archive.py's put_ia_bytes retry)."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    base = float(2**attempt)
    if resp.status_code == HTTP_SERVICE_UNAVAILABLE:
        return max(base, 15.0)
    return base
