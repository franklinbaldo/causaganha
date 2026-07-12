"""Internet Archive upload for TJRO JURIS parquet files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import httpx
import structlog

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

_HTTP_ERROR_THRESHOLD = 400
_HTTP_NOT_FOUND = 404


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


async def _put_object(local_path: Path, item_id: str, remote_name: str) -> None:
    """PUT *local_path* into IA *item_id* as *remote_name* (httpx, not boto3)."""
    auth = ia_s3.get_ia_s3_auth()
    if not auth:
        msg = "No IA S3 credentials found (IAS3_ACCESS_KEY / IAS3_SECRET_KEY)"
        raise RuntimeError(msg)

    url = f"https://s3.us.archive.org/{item_id}/{remote_name}"
    content = await anyio.Path(local_path).read_bytes()

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.put(url, content=content, headers=_upload_headers(auth))

    if resp.status_code >= _HTTP_ERROR_THRESHOLD:
        log.error(
            "ia_upload_failed",
            item_id=item_id,
            remote_name=remote_name,
            status=resp.status_code,
        )
        resp.raise_for_status()

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
