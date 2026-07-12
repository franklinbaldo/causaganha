"""Internet Archive upload for STJ acórdãos parquet files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from causaganha.pipeline.ia_s3 import meta_value as _meta_value


if TYPE_CHECKING:
    from pathlib import Path
import structlog


log = structlog.get_logger()

IA_ITEM_ID = "stj-acordaos-primeira-secao"
_IA_S3_BASE = f"https://s3.us.archive.org/{IA_ITEM_ID}"

MANIFEST_REMOTE_NAME = "stj-manifest.csv"
MANIFEST_DOWNLOAD_URL = f"https://archive.org/download/{IA_ITEM_ID}/{MANIFEST_REMOTE_NAME}"

HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_RETRIABLE = frozenset({408, 429, 500, 502, 503, 504})


def _build_auth_header(ia_key: str, ia_secret: str) -> str:
    return f"LOW {ia_key}:{ia_secret}"


def _build_upload_headers(ia_key: str, ia_secret: str, content_type: str) -> dict[str, str]:
    return {
        "Authorization": _build_auth_header(ia_key, ia_secret),
        "Content-Type": content_type,
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-subject": _meta_value("STJ;acórdãos;primeira seção;direito brasileiro"),
        "x-archive-meta-title": _meta_value("STJ Acórdãos — Primeira Seção"),
        "x-archive-meta-description": _meta_value(
            "Espelhos de acórdãos da Primeira Seção do Superior Tribunal de Justiça (STJ), "
            "obtidos via portal de dados abertos."
        ),
    }


def fetch_manifest(dest: Path) -> bool:
    """Restore the STJ manifest CSV from IA into *dest* (public read).

    Returns True when restored; False when the manifest is not on IA yet
    (first-ever run / item not created). Transport errors and non-404 HTTP
    errors raise — a flaky network must not silently look like "no manifest"
    (which would re-download and re-upload everything).
    """
    resp = httpx.get(MANIFEST_DOWNLOAD_URL, follow_redirects=True, timeout=60)
    if resp.status_code == _HTTP_NOT_FOUND:
        log.info("stj_manifest_not_on_ia", url=MANIFEST_DOWNLOAD_URL)
        return False
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    log.info("stj_manifest_restored_from_ia", url=MANIFEST_DOWNLOAD_URL, bytes=len(resp.content))
    return True


def upload_parquet(file_path: Path, ia_key: str, ia_secret: str) -> bool:
    """Upload a parquet file to the STJ IA item using httpx (NOT boto3).

    Uses ``x-archive-meta-*`` headers as required by IA S3-like API.

    Returns True on success, False on failure.
    """
    url = f"{_IA_S3_BASE}/{file_path.name}"
    headers = _build_upload_headers(ia_key, ia_secret, "application/octet-stream")
    content = file_path.read_bytes()

    log.info("stj_upload_starting", file=file_path.name, size=len(content), item=IA_ITEM_ID)

    max_retries = 5
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=300) as client:
                resp = client.put(url, content=content, headers=headers)
        except (httpx.HTTPError, httpx.RequestError) as exc:
            log.warning("stj_upload_http_error", attempt=attempt, error=str(exc))
            if attempt >= max_retries:
                return False
            continue

        if resp.status_code == HTTP_OK:
            log.info("stj_upload_complete", file=file_path.name, item=IA_ITEM_ID)
            return True

        if resp.status_code not in _RETRIABLE:
            log.warning(
                "stj_upload_failed_non_retriable",
                status=resp.status_code,
                file=file_path.name,
            )
            return False

        log.warning(
            "stj_upload_retriable_error",
            attempt=attempt,
            status=resp.status_code,
            file=file_path.name,
        )
        if attempt >= max_retries:
            break

    log.warning("stj_upload_exhausted_retries", file=file_path.name)
    return False
