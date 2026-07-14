"""Internet Archive upload for TJRO JURIS parquet files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from causaganha.pipeline import ia_s3


if TYPE_CHECKING:
    from pathlib import Path


log = structlog.get_logger()

IA_ITEM_PREFIX = "tjro-juris"

# The crawl/upload manifest lives in a dedicated (year-less) item so a fresh
# runner can restore state without enumerating yearly items. Public read —
# no credentials needed to download.
MANIFEST_ITEM_ID = "tjro-juris"
MANIFEST_REMOTE_NAME = "tjro-juris-manifest.csv"
MANIFEST_DOWNLOAD_URL = f"https://archive.org/download/{MANIFEST_ITEM_ID}/{MANIFEST_REMOTE_NAME}"

IA_ITEM_METADATA_TEMPLATE = {
    "mediatype": "data",
    "subject": "jurisprudencia; TJRO; Tribunal de Justica de Rondonia; direito",
    "description": (
        "Jurisprudência do Tribunal de Justiça de Rondônia (TJRO) — "
        "acórdãos, decisões, sentenças, votos, ementas e relatórios "
        "obtidos do sistema JURIS."
    ),
}

_HTTP_NOT_FOUND = 404

# IA's S3-compatible endpoint 503s ("Slow Down") under sustained upload
# volume — observed live during the 1988-2026 historical backfill (a whole
# year's worth of monthly parquets uploaded back-to-back with no delay).
# Without a retry here, a single 503 permanently failed that file until some
# much-later year's `upload` call happened to retry it (still with no
# backoff, so it just got Slow-Down'd again) — mirrors the tuning already
# proven in causaganha.pipeline.ia_s3._perform_upload (kept local: this
# module intentionally doesn't share retry state/config with that one).
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _is_retryable_upload_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS_CODES
    return isinstance(exc, httpx.RequestError)


def _item_id(year: int) -> str:
    return f"{IA_ITEM_PREFIX}-{year}"


def _upload_headers(auth: str) -> dict[str, str]:
    return {
        "Authorization": auth,
        "Content-Type": "application/octet-stream",
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": ia_s3.meta_value(IA_ITEM_METADATA_TEMPLATE["mediatype"]),
        "x-archive-meta-subject": ia_s3.meta_value(IA_ITEM_METADATA_TEMPLATE["subject"]),
        "x-archive-meta-description": ia_s3.meta_value(IA_ITEM_METADATA_TEMPLATE["description"]),
    }


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception(_is_retryable_upload_error),
    reraise=True,
)
async def _put_once(
    client: httpx.AsyncClient, url: str, content: bytes, headers: dict[str, str]
) -> httpx.Response:
    """Single PUT attempt; retries (503/429/5xx/network) handled by tenacity above."""
    resp = await client.put(url, content=content, headers=headers)
    resp.raise_for_status()
    return resp


async def _put_object(local_path: Path, item_id: str, remote_name: str) -> None:
    """PUT *local_path* into IA *item_id* as *remote_name* (httpx, not boto3)."""
    auth = ia_s3.get_ia_s3_auth()
    if not auth:
        msg = "No IA S3 credentials found (IAS3_ACCESS_KEY / IAS3_SECRET_KEY)"
        raise RuntimeError(msg)

    url = f"https://s3.us.archive.org/{item_id}/{remote_name}"
    content = await anyio.Path(local_path).read_bytes()
    headers = _upload_headers(auth)

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            await _put_once(client, url, content, headers)
        except httpx.HTTPStatusError as exc:
            log.exception(
                "ia_upload_failed",
                item_id=item_id,
                remote_name=remote_name,
                status=exc.response.status_code,
            )
            raise

    log.info(
        "ia_upload_ok",
        item_id=item_id,
        remote_name=remote_name,
        bytes=len(content),
    )


async def upload_file(local_path: Path, year: int, remote_name: str) -> None:
    """Upload local_path to tjro-juris-{year} IA item as remote_name."""
    await _put_object(local_path, _item_id(year), remote_name)


async def upload_manifest(local_path: Path) -> None:
    """Upload the crawl manifest CSV to its dedicated IA item."""
    await _put_object(local_path, MANIFEST_ITEM_ID, MANIFEST_REMOTE_NAME)


def download_manifest(dest: Path) -> bool:
    """Restore the manifest CSV from IA into *dest*.

    Returns True when restored; False when the manifest does not exist on IA
    yet (first-ever run / item not created). Transport errors and non-404
    HTTP errors raise — a flaky network must not silently look like "no
    manifest" (which would re-crawl and re-upload everything).
    """
    resp = httpx.get(MANIFEST_DOWNLOAD_URL, follow_redirects=True, timeout=60)
    if resp.status_code == _HTTP_NOT_FOUND:
        log.info("manifest_not_on_ia", url=MANIFEST_DOWNLOAD_URL)
        return False
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    log.info("manifest_restored_from_ia", url=MANIFEST_DOWNLOAD_URL, bytes=len(resp.content))
    return True
