"""Tests for tcu_acordaos.publish — IA upload + read-back proof (#1022).

#1020 already materializes the TCU TEOR Parquet locally; #1022's remaining gap is that
nothing ever proves the published bytes at the public URL match what was materialized.
A successful HTTP PUT is not itself evidence of that (upload_to_ia-style helpers elsewhere
in the repo never verify), so `verify_published` always re-downloads the artifact and
recomputes checksum/schema/count from those bytes — never from the local file it just
uploaded.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import unquote

import duckdb
import httpx
import pytest
import respx

from causaganha.decisoes.published import TCU_PARQUET_URL
from tcu_acordaos.publish import ITEM_ID, REMOTE_NAME, publish_parquet, verify_published


def _write_parquet(path: Path, *, rows: list[dict], visao_geral: bool = False) -> None:
    con = duckdb.connect()
    try:
        con.register("rows", rows)
        columns = "key, ano, acordao" + (", visao_geral" if visao_geral else "")
        con.execute(
            f"COPY (SELECT {columns} FROM rows) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        con.close()


@pytest.fixture
def local_parquet(tmp_path: Path) -> Path:
    path = tmp_path / "tcu-acordaos.parquet"
    _write_parquet(
        path,
        rows=[
            {"key": "TCU-2026-1", "ano": "2026", "acordao": "texto autoritativo 1"},
            {"key": "TCU-2026-2", "ano": "2026", "acordao": "texto autoritativo 2"},
        ],
    )
    return path


# ── publish_parquet (upload) ────────────────────────────────────────────────


def _upload_url() -> str:
    return f"https://s3.us.archive.org/{ITEM_ID}/{REMOTE_NAME}"


def test_publish_sends_ia_metadata_headers_and_bytes(local_parquet: Path):
    with respx.mock() as router:
        route = router.put(_upload_url()).respond(200)
        assert publish_parquet(local_parquet, ia_key="mykey", ia_secret="mysecret") is True

    request = route.calls.last.request
    assert request.headers["Authorization"] == "LOW mykey:mysecret"
    assert request.headers["x-archive-auto-make-bucket"] == "1"
    assert request.headers["x-archive-meta-mediatype"] == "data"
    title = request.headers["x-archive-meta-title"]
    assert unquote(title.removeprefix("uri(").removesuffix(")")) == "TCU — Acórdãos (TEOR)"
    assert not any(h.lower().startswith("x-amz-meta") for h in request.headers)
    assert request.content == local_parquet.read_bytes()


def test_publish_non_retriable_status_fails_once(local_parquet: Path):
    with respx.mock() as router:
        route = router.put(_upload_url()).respond(403)
        assert publish_parquet(local_parquet, ia_key="k", ia_secret="s") is False

    assert route.call_count == 1


def test_publish_retries_retriable_status_then_succeeds(local_parquet: Path):
    with respx.mock() as router:
        route = router.put(_upload_url())
        route.side_effect = [httpx.Response(503), httpx.Response(200)]
        assert publish_parquet(local_parquet, ia_key="k", ia_secret="s") is True

    assert route.call_count == 2


# ── verify_published (read-back proof) ──────────────────────────────────────


def test_verify_published_matches_local_artifact(local_parquet: Path):
    with respx.mock() as router:
        router.get(TCU_PARQUET_URL).respond(200, content=local_parquet.read_bytes())
        proof = verify_published(local_parquet)

    assert proof.published is True
    assert proof.checksum_matches_local is True
    assert proof.schema_ok is True
    assert proof.count_matches_local is True
    assert proof.record_count == 2
    assert proof.sha256 == hashlib.sha256(local_parquet.read_bytes()).hexdigest()
    assert proof.url == TCU_PARQUET_URL


def test_verify_published_detects_checksum_mismatch(local_parquet: Path, tmp_path: Path):
    stale = tmp_path / "stale.parquet"
    _write_parquet(stale, rows=[{"key": "TCU-2026-1", "ano": "2026", "acordao": "texto velho"}])

    with respx.mock() as router:
        router.get(TCU_PARQUET_URL).respond(200, content=stale.read_bytes())
        proof = verify_published(local_parquet)

    assert proof.published is False
    assert proof.checksum_matches_local is False


def test_verify_published_detects_row_count_mismatch(local_parquet: Path, tmp_path: Path):
    fewer_rows = tmp_path / "fewer.parquet"
    _write_parquet(fewer_rows, rows=[{"key": "TCU-2026-1", "ano": "2026", "acordao": "x"}])

    with respx.mock() as router:
        router.get(TCU_PARQUET_URL).respond(200, content=fewer_rows.read_bytes())
        proof = verify_published(local_parquet)

    assert proof.published is False
    assert proof.count_matches_local is False


def test_verify_published_rejects_visao_geral_column(local_parquet: Path, tmp_path: Path):
    tainted = tmp_path / "tainted.parquet"
    _write_parquet(
        tainted,
        rows=[
            {"key": "TCU-2026-1", "ano": "2026", "acordao": "x", "visao_geral": "resumo IA"},
            {"key": "TCU-2026-2", "ano": "2026", "acordao": "y", "visao_geral": "resumo IA"},
        ],
        visao_geral=True,
    )

    with respx.mock() as router:
        router.get(TCU_PARQUET_URL).respond(200, content=tainted.read_bytes())
        proof = verify_published(tainted)

    assert proof.published is False
    assert proof.schema_ok is False


def test_verify_published_missing_key_column_fails_schema(tmp_path: Path):
    no_key = tmp_path / "no-key.parquet"
    con = duckdb.connect()
    try:
        con.execute(f"COPY (SELECT 'x' AS ano) TO '{no_key}' (FORMAT PARQUET)")
    finally:
        con.close()

    with respx.mock() as router:
        router.get(TCU_PARQUET_URL).respond(200, content=no_key.read_bytes())
        proof = verify_published(no_key)

    assert proof.published is False
    assert proof.schema_ok is False
