"""Tests for datajud.archive — parquet build, IA headers, retry discipline."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

import duckdb
import httpx
import pytest
import respx

from datajud.archive import (
    CAPA_SCHEMA,
    MOVIMENTOS_SCHEMA,
    capa_parquet_name,
    item_id,
    movimentos_parquet_name,
    upload_parquet,
    write_capa_parquet,
    write_movimentos_parquet,
)


if TYPE_CHECKING:
    from pathlib import Path


CNJ = "00000010220248220001"


def _capa_row(**overrides: object) -> dict:
    row = {
        "numero_processo": CNJ,
        "tribunal": "TJRO",
        "grau": "G1",
        "orgao_julgador_codigo": 111,
        "orgao_julgador": "1ª Vara Cível",
        "classe_codigo": 7,
        "classe_nome": "Procedimento Comum Cível",
        "assuntos": "Dano Material; Dano Moral",
        "sistema": "PJE",
        "formato": "Eletrônico",
        "nivel_sigilo": 0,
        "data_ajuizamento": "2024-01-15T10:30:00",
        "ultima_atualizacao": "2026-06-13T09:45:09.000Z",
        "n_movimentos": 2,
        "consultado_em": "2026-07-07T00:00:00+00:00",
    }
    row.update(overrides)
    return row


# ── Naming ───────────────────────────────────────────────────────────────


def test_item_and_parquet_naming():
    assert item_id("TJRO") == "datajud-tjro"
    assert capa_parquet_name("tjro") == "datajud-capa-tjro.parquet"
    assert movimentos_parquet_name("TJRO") == "datajud-movimentos-tjro.parquet"


# ── Parquet build ────────────────────────────────────────────────────────


def test_write_capa_parquet_roundtrip(tmp_path: Path):
    path = tmp_path / "capa.parquet"
    count = write_capa_parquet([_capa_row(), _capa_row(grau="G2", orgao_julgador_codigo=222)], path)
    assert count == 2

    con = duckdb.connect()
    rows = con.execute(f"SELECT * FROM read_parquet('{path}') ORDER BY grau").fetchall()
    columns = [d[0] for d in con.description]
    con.close()
    assert columns == CAPA_SCHEMA.names
    first = dict(zip(columns, rows[0], strict=False))
    assert first["numero_processo"] == CNJ
    assert first["data_ajuizamento"] == "2024-01-15T10:30:00"
    assert first["n_movimentos"] == 2


def test_write_capa_parquet_tolerates_missing_and_extra_keys(tmp_path: Path):
    path = tmp_path / "capa.parquet"
    row = {"numero_processo": CNJ, "grau": "G1", "unknown_column": "ignored"}
    assert write_capa_parquet([row], path) == 1

    con = duckdb.connect()
    result = con.execute(
        f"SELECT numero_processo, classe_nome, nivel_sigilo FROM read_parquet('{path}')"
    ).fetchone()
    con.close()
    assert result == (CNJ, None, None)


def test_write_movimentos_parquet_roundtrip(tmp_path: Path):
    path = tmp_path / "mov.parquet"
    rows = [
        {
            "numero_processo": CNJ,
            "tribunal": "TJRO",
            "grau": "G1",
            "orgao_julgador_codigo": 111,
            "codigo": 26,
            "nome": "Distribuição",
            "data_hora": "2024-01-15T10:30:00.000Z",
            "complementos": "tipo=sorteio",
        }
    ]
    assert write_movimentos_parquet(rows, path) == 1

    con = duckdb.connect()
    cols = [d[0] for d in con.execute(f"SELECT * FROM read_parquet('{path}')").description]
    con.close()
    assert cols == MOVIMENTOS_SCHEMA.names


def test_write_empty_parquet_keeps_schema(tmp_path: Path):
    path = tmp_path / "empty.parquet"
    assert write_capa_parquet([], path) == 0
    con = duckdb.connect()
    cols = [d[0] for d in con.execute(f"SELECT * FROM read_parquet('{path}')").description]
    con.close()
    assert cols == CAPA_SCHEMA.names


# ── IA upload ────────────────────────────────────────────────────────────


@pytest.fixture
def parquet_file(tmp_path: Path) -> Path:
    p = tmp_path / "datajud-capa-tjro.parquet"
    p.write_bytes(b"PAR1-fake-bytes")
    return p


def _upload_url(name: str) -> str:
    return f"https://s3.us.archive.org/datajud-tjro/{name}"


def test_upload_sends_ia_metadata_headers(parquet_file: Path):
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(200)
        assert upload_parquet(parquet_file, "tjro", "mykey", "mysecret") is True

    request = route.calls.last.request
    assert request.headers["Authorization"] == "LOW mykey:mysecret"
    assert request.headers["x-archive-auto-make-bucket"] == "1"
    assert request.headers["x-archive-meta-mediatype"] == "data"
    # Non-ASCII metadata must use IA's uri(...) percent-encoding convention —
    # raw UTF-8 in a header would crash httpx with UnicodeEncodeError.
    title = request.headers["x-archive-meta-title"]
    assert title.startswith("uri(")
    assert title.endswith(")")
    assert title.isascii()
    assert unquote(title[4:-1]) == "DataJud — Metadados Processuais (TJRO)"
    assert request.headers["x-archive-meta-description"].isascii()
    assert request.headers["x-archive-meta-subject"].isascii()
    # IA wants x-archive-meta-*, never boto3-style x-amz-meta-* (CLAUDE.md)
    assert not any(h.lower().startswith("x-amz-meta") for h in request.headers)
    assert request.content == b"PAR1-fake-bytes"


def test_upload_403_is_non_retriable_and_fails_once(parquet_file: Path):
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(403)
        assert upload_parquet(parquet_file, "tjro", "k", "s") is False

    assert route.call_count == 1


def test_upload_retries_retriable_status_then_succeeds(parquet_file: Path):
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name))
        route.side_effect = [httpx.Response(503), httpx.Response(200)]
        assert upload_parquet(parquet_file, "tjro", "k", "s") is True

    assert route.call_count == 2


def test_upload_exhausts_retries_on_persistent_503(parquet_file: Path):
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name)).respond(503)
        assert upload_parquet(parquet_file, "tjro", "k", "s") is False

    # max_retries=5 → initial attempt + 5 retries
    assert route.call_count == 6


def test_upload_network_error_retries_then_fails(parquet_file: Path):
    with respx.mock() as router:
        route = router.put(_upload_url(parquet_file.name))
        route.side_effect = httpx.ConnectError("connection refused")
        assert upload_parquet(parquet_file, "tjro", "k", "s") is False

    assert route.call_count == 6
