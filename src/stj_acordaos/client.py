"""HTTP client for the STJ open data portal (CKAN API)."""

from __future__ import annotations

import random
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import structlog

from common.relay import relay_transport_from_env


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn

log = structlog.get_logger()

PORTAL_URL = "https://dadosabertos.web.stj.jus.br/dataset/espelhos-de-acordaos-primeira-secao"
DATASET_API_URL = (
    "https://dadosabertos.web.stj.jus.br/api/3/action/package_show"
    "?id=a96a175b-a54b-4bfd-82b8-fcd7cc0200bc"
)

HTTP_FORBIDDEN = 403
MAX_ATTEMPTS = 4
_BASE_DELAY_S = 2.0

# Unlike djen_backup (where 403 means "back off, never retry blindly"), the
# STJ WAF intermittently 403-blocks whole IP ranges — notably GitHub-hosted
# runners — while the API stays up for everyone else. A later attempt from
# the same host can succeed, so 403 is retriable here.
_RETRIABLE_STATUS: frozenset[int] = frozenset({403, 408, 429, 500, 502, 503, 504})

# The STJ WAF is more likely to block non-browser User-Agents (the httpx
# default is a known trigger). Present realistic browser headers.
_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


class STJWAFBlockedError(httpx.HTTPStatusError):
    """The STJ WAF kept returning 403 after all retry attempts.

    Distinguishes "this network is blocked by the STJ WAF" (the API itself is
    healthy) from ordinary HTTP failures. Subclasses ``httpx.HTTPStatusError``
    so existing call sites that catch that type keep working.
    """


def _make_client() -> httpx.Client:
    """Create a configured synchronous HTTP client.

    Routes through the relay (see ``common.relay``) when ``RELAY_URL``/
    ``RELAY_TOKEN`` are set — used in CI, where the STJ WAF blocks GitHub
    runner IP ranges. Direct connection otherwise (local/dev default).
    """
    return httpx.Client(
        timeout=120,
        follow_redirects=True,
        headers=_BROWSER_HEADERS,
        transport=relay_transport_from_env(),
    )


def _sleep(seconds: float) -> None:
    """Sleep indirection so tests can patch the backoff away."""
    time.sleep(seconds)


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff (2s, 4s, 8s, ...) with up to 25% jitter."""
    base = _BASE_DELAY_S * (2**attempt)
    return base * (1.0 + random.uniform(0.0, 0.25))  # noqa: S311 — jitter, not crypto


def _raise_exhausted(url: str, last_exc: httpx.HTTPError, attempts: int) -> NoReturn:
    """Re-raise the final failure, upgrading a persistent 403 to a WAF error."""
    if (
        isinstance(last_exc, httpx.HTTPStatusError)
        and last_exc.response.status_code == HTTP_FORBIDDEN
    ):
        msg = (
            f"STJ WAF blocked: HTTP 403 from {url} after {attempts} attempts. "
            "The CKAN API is reachable from other networks; this host's IP range "
            "(e.g. GitHub-hosted runners) is likely blocked by the STJ WAF."
        )
        raise STJWAFBlockedError(
            msg, request=last_exc.request, response=last_exc.response
        ) from last_exc
    raise last_exc


def _retrying[T](op: Callable[[], T], url: str, *, max_attempts: int = MAX_ATTEMPTS) -> T:
    """Run *op*, retrying on transport errors and retriable HTTP statuses.

    Retriable: transport/timeout errors and HTTP 403/408/429/5xx. Other
    status errors (e.g. 404) raise immediately. After the final attempt,
    a persistent 403 is raised as :class:`STJWAFBlockedError`; anything
    else re-raises the last underlying error.
    """
    last_exc: httpx.HTTPError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = op()
        except httpx.TransportError as exc:
            last_exc = exc
            log.warning("stj_transport_error", url=url, attempt=attempt, error=str(exc))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in _RETRIABLE_STATUS:
                raise
            last_exc = exc
            log.warning(
                "stj_retriable_status",
                url=url,
                attempt=attempt,
                status=exc.response.status_code,
            )
        else:
            return result
        if attempt < max_attempts:
            delay = _backoff_delay(attempt - 1)
            log.info("stj_retry_backoff", url=url, attempt=attempt, sleep_s=round(delay, 1))
            _sleep(delay)
    if last_exc is None:  # pragma: no cover
        msg = "unreachable"
        raise RuntimeError(msg)
    _raise_exhausted(url, last_exc, max_attempts)


def _get_checked(client: httpx.Client, url: str) -> httpx.Response:
    """GET *url* and raise for any error status."""
    resp = client.get(url)
    resp.raise_for_status()
    return resp


def get_resource_list() -> list[dict]:
    """Fetch the resource list from the STJ CKAN dataset API.

    Returns a list of resource dicts with keys like ``url``, ``name``,
    ``format``, ``last_modified``, etc.

    Retries transient failures (403 from the STJ WAF, 429, 5xx, transport
    errors) with exponential backoff; a persistent 403 raises
    :class:`STJWAFBlockedError`.
    """
    with _make_client() as client:
        resp = _retrying(lambda: _get_checked(client, DATASET_API_URL), DATASET_API_URL)
    data = resp.json()
    if not data.get("success"):
        msg = f"CKAN API returned success=false: {data.get('error')}"
        raise RuntimeError(msg)
    resources: list[dict] = data.get("result", {}).get("resources", [])
    log.info("stj_resource_list_fetched", count=len(resources))
    return resources


def _stream_to_file(client: httpx.Client, url: str, dest_path: Path) -> None:
    """Stream *url* into *dest_path*, removing any partial file on failure."""
    try:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with dest_path.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    fh.write(chunk)
    except httpx.HTTPError:
        dest_path.unlink(missing_ok=True)
        raise


def download_resource(url: str, dest_path: Path) -> None:
    """Download a resource file (ZIP or JSON) to *dest_path*.

    Streams the response to avoid loading large files into memory. Transient
    failures (403/429/5xx, transport errors) are retried with backoff; each
    failed attempt cleans up its partial file before retrying.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with _make_client() as client:
        _retrying(lambda: _stream_to_file(client, url, dest_path), url)
    log.info("stj_resource_downloaded", url=url, dest=str(dest_path), size=dest_path.stat().st_size)


def _safe_member(member: zipfile.ZipInfo) -> bool:
    """Return True if the ZIP member is safe to extract.

    Rejects:
    - Members with ``..`` in their path (path traversal)
    - Absolute paths
    - Non-JSON files
    """
    name = member.filename
    if ".." in name or name.startswith("/"):
        return False
    return name.lower().endswith(".json")


def extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    """Safely extract JSON files from a ZIP archive.

    Validates all member paths before extraction. Only ``.json`` files
    are extracted; path-traversal members are skipped with a warning.

    Returns a list of extracted file paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            if not _safe_member(member):
                log.warning("stj_zip_skipped_member", member=member.filename, zip=str(zip_path))
                continue
            out_path = dest_dir / Path(member.filename).name
            out_path.write_bytes(zf.read(member.filename))
            extracted.append(out_path)
    log.info("stj_zip_extracted", zip=str(zip_path), count=len(extracted), dest=str(dest_dir))
    return extracted
