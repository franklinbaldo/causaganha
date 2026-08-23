"""Parquet build + Internet Archive transfer for DataJud metadata.

Capa and movimentos live in separate parquet files (a process can have
hundreds of movements; the capa stays light for joins):

- ``datajud-capa-{tribunal}.parquet``
- ``datajud-movimentos-{tribunal}.parquet``

Both go to the IA item ``datajud-{tribunal}`` via httpx (NOT boto3 — IA
wants ``x-archive-meta-*`` headers), with the ``uri(...)`` percent-encode
convention for non-ASCII metadata values (see
``causaganha.pipeline.ia_s3.meta_value``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from causaganha.pipeline.ia_s3 import meta_value as _meta_value


if TYPE_CHECKING:
    from pathlib import Path


log = structlog.get_logger()

HTTP_OK = 200
HTTP_NOT_FOUND = 404
_RETRIABLE = frozenset({408, 429, 500, 502, 503, 504})
_MAX_RETRIES = 5

CAPA_SCHEMA = pa.schema(
    [
        pa.field("numero_processo", pa.string()),
        pa.field("tribunal", pa.string()),
        pa.field("grau", pa.string()),
        pa.field("orgao_julgador_codigo", pa.int64()),
        pa.field("orgao_julgador", pa.string()),
        pa.field("classe_codigo", pa.int64()),
        pa.field("classe_nome", pa.string()),
        pa.field("assuntos", pa.string()),
        pa.field("sistema", pa.string()),
        pa.field("formato", pa.string()),
        pa.field("nivel_sigilo", pa.int64()),
        pa.field("data_ajuizamento", pa.string()),
        pa.field("ultima_atualizacao", pa.string()),
        pa.field("n_movimentos", pa.int64()),
        pa.field("consultado_em", pa.string()),
    ]
)

MOVIMENTOS_SCHEMA = pa.schema(
    [
        pa.field("numero_processo", pa.string()),
        pa.field("tribunal", pa.string()),
        pa.field("grau", pa.string()),
        pa.field("orgao_julgador_codigo", pa.int64()),
        pa.field("codigo", pa.int64()),
        pa.field("nome", pa.string()),
        pa.field("data_hora", pa.string()),
        pa.field("complementos", pa.string()),
    ]
)


def item_id(tribunal: str) -> str:
    """IA item identifier for a tribunal (``datajud-{tribunal}``)."""
    return f"datajud-{tribunal.lower()}"


def capa_parquet_name(tribunal: str) -> str:
    """Canonical capa parquet filename for a tribunal."""
    return f"datajud-capa-{tribunal.lower()}.parquet"


def movimentos_parquet_name(tribunal: str) -> str:
    """Canonical movimentos parquet filename for a tribunal."""
    return f"datajud-movimentos-{tribunal.lower()}.parquet"


def write_capa_parquet(rows: list[dict], path: Path) -> int:
    """Write capa rows to *path* with the canonical schema. Returns row count."""
    return _write_parquet(rows, CAPA_SCHEMA, path)


def write_movimentos_parquet(rows: list[dict], path: Path) -> int:
    """Write movimento rows to *path* with the canonical schema. Returns row count."""
    return _write_parquet(rows, MOVIMENTOS_SCHEMA, path)


def _write_parquet(rows: list[dict], schema: pa.Schema, path: Path) -> int:
    filtered = [{name: row.get(name) for name in schema.names} for row in rows]
    table = pa.Table.from_pylist(filtered, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd")
    log.info("datajud_parquet_written", path=str(path), rows=table.num_rows)
    return table.num_rows


# ── IA transfer ──────────────────────────────────────────────────────────


def _build_upload_headers(ia_key: str, ia_secret: str, tribunal: str) -> dict[str, str]:
    sigla = tribunal.upper()
    return {
        "Authorization": f"LOW {ia_key}:{ia_secret}",
        "Content-Type": "application/octet-stream",
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-subject": _meta_value(
            f"DataJud;CNJ;{sigla};metadados processuais;movimentação processual"
        ),
        "x-archive-meta-title": _meta_value(f"DataJud — Metadados Processuais ({sigla})"),
        "x-archive-meta-description": _meta_value(
            f"Capa e movimentação processual do {sigla} obtidas da API Pública "
            "do DataJud (CNJ) — classe, assuntos, órgão julgador, grau e a "
            "linha de movimentação das tabelas processuais unificadas."
        ),
    }


def _download_url(file_name: str, tribunal: str) -> str:
    return f"https://archive.org/download/{item_id(tribunal)}/{file_name}"


def download_file(file_name: str, tribunal: str) -> bytes | None:
    """Download one file from the tribunal item.

    Returns ``None`` only for a definitive HTTP 404. Transport failures,
    exhausted transient statuses and other HTTP errors raise ``OSError`` so a
    caller cannot accidentally treat an unavailable remote state as bootstrap.
    """
    url = _download_url(file_name, tribunal)
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = client.get(url)
            except httpx.HTTPError as exc:
                log.warning(
                    "datajud_download_http_error",
                    attempt=attempt,
                    file=file_name,
                    error=str(exc),
                )
                if attempt >= _MAX_RETRIES:
                    msg = f"Internet Archive download failed for {file_name}: {exc}"
                    raise OSError(msg) from exc
                continue

            if response.status_code == HTTP_OK:
                return response.content
            if response.status_code == HTTP_NOT_FOUND:
                return None
            if response.status_code not in _RETRIABLE:
                msg = f"Internet Archive returned HTTP {response.status_code} for {file_name}"
                raise OSError(msg)

            log.warning(
                "datajud_download_retriable_error",
                attempt=attempt,
                status=response.status_code,
                file=file_name,
            )
            if attempt >= _MAX_RETRIES:
                msg = f"Internet Archive download exhausted retries for {file_name}"
                raise OSError(msg)

    msg = f"Internet Archive download failed for {file_name}"
    raise OSError(msg)


def upload_file(file_path: Path, tribunal: str, ia_key: str, ia_secret: str) -> bool:
    """Upload one DataJud artifact to the tribunal IA item via httpx.

    Retries transient statuses/transport errors; returns ``True`` on success.
    The artifact may be a Parquet or the coherent state bundle.
    """
    url = f"https://s3.us.archive.org/{item_id(tribunal)}/{file_path.name}"
    headers = _build_upload_headers(ia_key, ia_secret, tribunal)
    content = file_path.read_bytes()

    log.info(
        "datajud_upload_starting",
        file=file_path.name,
        size=len(content),
        item=item_id(tribunal),
    )

    with httpx.Client(timeout=300) as client:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = client.put(url, content=content, headers=headers)
            except (httpx.HTTPError, httpx.RequestError) as exc:
                log.warning("datajud_upload_http_error", attempt=attempt, error=str(exc))
                if attempt >= _MAX_RETRIES:
                    return False
                continue

            if resp.status_code == HTTP_OK:
                log.info("datajud_upload_complete", file=file_path.name, item=item_id(tribunal))
                return True

            if resp.status_code not in _RETRIABLE:
                log.warning(
                    "datajud_upload_failed_non_retriable",
                    status=resp.status_code,
                    file=file_path.name,
                )
                return False

            log.warning(
                "datajud_upload_retriable_error",
                attempt=attempt,
                status=resp.status_code,
                file=file_path.name,
            )
            if attempt >= _MAX_RETRIES:
                break

    log.warning("datajud_upload_exhausted_retries", file=file_path.name)
    return False


def upload_parquet(file_path: Path, tribunal: str, ia_key: str, ia_secret: str) -> bool:
    """Backward-compatible wrapper for callers that publish one Parquet."""
    return upload_file(file_path, tribunal, ia_key, ia_secret)
