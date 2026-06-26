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


def _item_id(year: int) -> str:
    return f"{IA_ITEM_PREFIX}-{year}"


async def upload_file(local_path: Path, year: int, remote_name: str) -> None:
    """Upload local_path to tjro-juris-{year} IA item as remote_name."""
    auth = ia_s3.get_ia_s3_auth()
    if not auth:
        msg = "No IA S3 credentials found (IAS3_ACCESS_KEY / IAS3_SECRET_KEY)"
        raise RuntimeError(msg)

    item_id = _item_id(year)
    url = f"https://s3.us.archive.org/{item_id}/{remote_name}"

    content = await anyio.Path(local_path).read_bytes()
    headers = {
        "Authorization": auth,
        "Content-Type": "application/octet-stream",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": IA_ITEM_METADATA_TEMPLATE["mediatype"],
        "x-archive-meta-subject": IA_ITEM_METADATA_TEMPLATE["subject"],
        "x-archive-meta-description": IA_ITEM_METADATA_TEMPLATE["description"],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.put(url, content=content, headers=headers)

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
