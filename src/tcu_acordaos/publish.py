"""Publish the materialized TCU TEOR Parquet to Internet Archive, with read-back proof (#1022).

#1020 already produces a queryable, provenance-complete Parquet locally
(`tcu_acordaos.materialize`); this module closes the remaining gap: nothing
in the repo previously proved that a *published* artifact's bytes actually
match what was materialized. A successful HTTP PUT is not that proof — it
only means Internet Archive accepted the request, not that the bytes are
readable at the public URL with the expected schema/row count (the same
discipline `reconcile_processos.upload_to_ia`/`datajud.archive.upload_file`
never apply, since neither of them re-reads what they just uploaded).

`publish_parquet` follows the same IA transfer contract already used
throughout the repo (httpx, never boto3 — IA wants `x-archive-meta-*`
headers, not `x-amz-meta-*`) and the same target the search surface
(`causaganha.decisoes.published.TCU_PARQUET_URL`) is already wired against,
so this module cannot introduce a second, drifting notion of "where TCU
lives on IA". `verify_published` always re-downloads from that same public
URL and recomputes checksum/schema/count from those bytes — never from the
local file it just uploaded — before a caller may treat the artifact as
published.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb
import httpx

from causaganha.decisoes.published import TCU_PARQUET_URL
from causaganha.pipeline.ia_s3 import meta_value as _meta_value


ITEM_ID = "tcu-acordaos-2017-2026"
REMOTE_NAME = "tcu-acordaos.parquet"

_UPLOAD_URL = f"https://s3.us.archive.org/{ITEM_ID}/{REMOTE_NAME}"

_HTTP_OK = 200
_RETRIABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
_MAX_RETRIES = 5

_REQUIRED_COLUMNS = frozenset({"key"})
_FORBIDDEN_COLUMNS = frozenset({"visao_geral", "VISAOGERAL"})


def _build_upload_headers(ia_key: str, ia_secret: str) -> dict[str, str]:
    return {
        "Authorization": f"LOW {ia_key}:{ia_secret}",
        "Content-Type": "application/octet-stream",
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-subject": _meta_value(
            "TCU;Tribunal de Contas da União;controle externo;acórdãos;jurisprudência"
        ),
        "x-archive-meta-title": _meta_value("TCU — Acórdãos (TEOR)"),
        "x-archive-meta-description": _meta_value(
            "Acórdãos do Tribunal de Contas da União (TEOR autoritativo, sem VISAOGERAL) "
            "derivados dos CSVs oficiais de Dados Abertos do TCU, com proveniência até o "
            "arquivo/SHA-256 de origem."
        ),
    }


def publish_parquet(
    path: Path,
    *,
    ia_key: str,
    ia_secret: str,
    timeout: float = 300,
    max_retries: int = _MAX_RETRIES,
) -> bool:
    """Upload *path* to the TCU IA item. Returns True only on a 200 response.

    Retries transient statuses; a non-retriable status (e.g. 403/404) fails
    immediately rather than burning the retry budget on a request that will
    never succeed.
    """
    content = path.read_bytes()
    headers = _build_upload_headers(ia_key, ia_secret)
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = client.put(_UPLOAD_URL, content=content, headers=headers)
            except (httpx.HTTPError, httpx.RequestError):
                if attempt >= max_retries:
                    return False
                continue

            if resp.status_code == _HTTP_OK:
                return True
            if resp.status_code not in _RETRIABLE_STATUSES:
                return False
            if attempt >= max_retries:
                return False

    return False


@dataclass(frozen=True, slots=True)
class PublicationProof:
    """Evidence gathered by re-downloading a published artifact from its public URL.

    `published` is the single gate #1022 needs: a caller must never announce
    coverage for a year based on upload success alone, only on this proof.
    """

    url: str
    size_bytes: int
    sha256: str
    record_count: int
    checksum_matches_local: bool
    schema_ok: bool
    count_matches_local: bool

    @property
    def published(self) -> bool:
        return self.checksum_matches_local and self.schema_ok and self.count_matches_local


def _parquet_row_count(path: Path) -> int:
    con = duckdb.connect()
    try:
        return con.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
    finally:
        con.close()


def verify_published(
    local_path: Path,
    *,
    url: str = TCU_PARQUET_URL,
    timeout: float = 300,
) -> PublicationProof:
    """Re-download *url* and verify it matches the local artifact at *local_path*.

    Checksum, schema (`key` present, VISAOGERAL absent) and row count are all
    derived from the freshly downloaded bytes, never from the upload request
    or the local file's own row count read a second time from disk — the
    downloaded copy is genuinely re-parsed on its own.
    """
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
    resp.raise_for_status()
    remote_bytes = resp.content
    remote_sha256 = hashlib.sha256(remote_bytes).hexdigest()
    local_sha256 = hashlib.sha256(local_path.read_bytes()).hexdigest()

    tmp = local_path.with_name(f".{local_path.name}.readback")
    tmp.write_bytes(remote_bytes)
    try:
        con = duckdb.connect()
        try:
            columns = {
                row[0]
                for row in con.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)", [str(tmp)]
                ).fetchall()
            }
            record_count = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)", [str(tmp)]
            ).fetchone()[0]
        finally:
            con.close()
    finally:
        tmp.unlink(missing_ok=True)

    schema_ok = _REQUIRED_COLUMNS <= columns and not (columns & _FORBIDDEN_COLUMNS)

    return PublicationProof(
        url=url,
        size_bytes=len(remote_bytes),
        sha256=remote_sha256,
        record_count=record_count,
        checksum_matches_local=remote_sha256 == local_sha256,
        schema_ok=schema_ok,
        count_matches_local=record_count == _parquet_row_count(local_path),
    )
