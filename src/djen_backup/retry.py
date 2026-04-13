"""HTTP request retry logic with exponential backoff."""

from __future__ import annotations

import asyncio

import httpx
import structlog


log = structlog.get_logger()

# HTTP status constants
HTTP_BAD_REQUEST = 400
HTTP_SERVICE_UNAVAILABLE = 503

RETRIABLE_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


def _should_retry(
    resp: httpx.Response,
    attempt: int,
    max_retries: int,
    *,
    retry_djen_400: bool,
    retry_404: bool,
) -> float | None:
    """Return wait time if this response should be retried, else None."""
    if attempt >= max_retries:
        return None

    if resp.status_code in RETRIABLE_STATUS_CODES:
        return _backoff(attempt, resp)

    if retry_djen_400 and resp.status_code == HTTP_BAD_REQUEST:
        return _backoff(attempt, resp)

    if retry_404 and resp.status_code == 404:
        return _backoff(attempt, resp)

    return None


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
    - Network / transport errors
    - Status codes: 408, 429, 500, 502, 503, 504
    - DJEN proxy 400 (transient) when *retry_djen_400* is True

    Respects ``Retry-After`` header when present.
    """
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.request(
                method,
                url,
                content=content,
                headers=headers,
            )
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = max(5.0, float(2**attempt))
                log.warning(
                    "http_transport_retry",
                    url=url,
                    error=str(exc),
                    attempt=attempt + 1,
                    wait_s=wait,
                )
                await asyncio.sleep(wait)
                continue
            raise
        else:
            wait = _should_retry(
                resp,
                attempt,
                max_retries,
                retry_djen_400=retry_djen_400,
                retry_404=retry_404,
            )
            if wait is not None:
                log.warning(
                    "http_retry",
                    url=url,
                    status=resp.status_code,
                    attempt=attempt + 1,
                    wait_s=wait,
                )
                await asyncio.sleep(wait)
                continue

            return resp

    # Should not reach here, but satisfy the type checker
    if last_exc is not None:
        raise last_exc  # pragma: no cover
    msg = "Exhausted retries"  # pragma: no cover
    raise RuntimeError(msg)  # pragma: no cover


def _backoff(attempt: int, resp: httpx.Response) -> float:
    """Compute wait time, respecting Retry-After header.

    For 503 responses (IA rate limit / new-item creation), use a minimum
    of 10 seconds to give IA time to process before retrying.
    """
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(float(retry_after), 1.0)
        except ValueError:
            pass
    base = float(2**attempt)
    # IA S3 503 needs longer minimum backoff — item creation is rate-limited
    if resp.status_code == HTTP_SERVICE_UNAVAILABLE:
        return max(base, 15.0)
    return base
