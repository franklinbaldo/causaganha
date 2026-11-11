"""Tests for daily ZIP packaging, resolution index updates, and CNJ sequence extrapolation.

Zero real network. Tests end-to-end compression, unzipping, Parquet indexing, and Modulo 97.
"""

from __future__ import annotations

import gzip
import json
import zipfile
from typing import TYPE_CHECKING

import pyarrow.parquet as pq
import pytest

from causaganha.processos.cnj import (
    calcular_digito_verificador,
    extrapolar_sequencia_cnj,
    gerar_cnj,
    validar_digito_verificador,
)
from datajud.daily_pack import (
    pack_daily_zip,
    update_resolution_index,
)


if TYPE_CHECKING:
    from pathlib import Path


CNJ_REF = "00012344520268220001"


# ── CNJ Modulo 97 and Extrapolation Tests ─────────────────────────────────


def test_calcular_digito_verificador_and_gerar_cnj():
    # Sequence: 1234, Year: 2026, JTR: 822 (TJRO), Organ: 0001
    dv = calcular_digito_verificador(1234, 2026, "822", "0001")
    cnj = gerar_cnj(1234, 2026, "822", "0001")

    assert len(dv) == 2
    assert len(cnj) == 20
    assert cnj[0:7] == "0001234"
    assert cnj[7:9] == dv
    assert cnj[9:13] == "2026"
    assert cnj[13:16] == "822"
    assert cnj[16:20] == "0001"

    # Must be valid under official CNJ Modulo 97 check
    assert validar_digito_verificador(cnj) is True


def test_extrapolar_sequencia_cnj_generates_valid_cnjs():
    base_cnj = gerar_cnj(500, 2026, "822", "0001")
    assert validar_digito_verificador(base_cnj) is True

    # Generate next 5 sequential processes
    proximos = extrapolar_sequencia_cnj(base_cnj, quantidade=5, avancar=True)
    assert len(proximos) == 5

    for idx, cnj in enumerate(proximos, start=1):
        assert int(cnj[0:7]) == 500 + idx
        assert cnj[9:13] == "2026"
        assert cnj[13:16] == "822"
        assert cnj[16:20] == "0001"
        assert validar_digito_verificador(cnj) is True

    # Generate previous 3 sequential processes
    anteriores = extrapolar_sequencia_cnj(base_cnj, quantidade=3, avancar=False)
    assert len(anteriores) == 3
    for idx, cnj in enumerate(anteriores, start=1):
        assert int(cnj[0:7]) == 500 - idx
        assert validar_digito_verificador(cnj) is True


def test_extrapolar_sequencia_invalid_cnj_raises():
    with pytest.raises(ValueError, match="CNJ inválido"):
        extrapolar_sequencia_cnj("invalid-cnj", 5)


# ── Daily ZIP Packaging Tests ─────────────────────────────────────────────


def test_pack_daily_zip_creates_transparent_unzip_structure(tmp_path: Path):
    daily_dir = tmp_path / "daily"
    doc1 = {
        "numeroProcesso": CNJ_REF,
        "grau": "G1",
        "tribunal": "TJRO",
        "dataHoraUltimaAtualizacao": "2026-11-10T10:00:00.000Z",
        "movimentos": [{"codigo": 26, "nome": "Distribuição"}],
    }

    zip_path, count = pack_daily_zip(
        [doc1],
        tribunal="tjro",
        target_date="2026-11-10",
        output_dir=daily_dir,
        compress_internal_json=True,
    )

    assert zip_path.exists()
    assert count == 1
    assert zip_path.name == "tjro_2026-11-10.zip"

    # Verify transparent unzip contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        expected_name = f"{CNJ_REF}.json.gz"
        assert expected_name in namelist

        with zf.open(expected_name) as entry:
            content = gzip.decompress(entry.read())
            restored = json.loads(content.decode("utf-8"))
            assert restored["numeroProcesso"] == CNJ_REF
            assert len(restored["movimentos"]) == 1
            assert restored["movimentos"][0]["nome"] == "Distribuição"


def test_pack_daily_zip_empty(tmp_path: Path):
    daily_dir = tmp_path / "daily"
    zip_path, count = pack_daily_zip(
        [], tribunal="tjro", target_date="2026-11-10", output_dir=daily_dir
    )
    assert count == 0


# ── Resolution Index Parquet Tests ───────────────────────────────────────


def test_update_resolution_index(tmp_path: Path):
    index_file = tmp_path / "index" / "indice_processos_tjro.parquet"
    cnj2 = gerar_cnj(999, 2026, "822", "0001")

    doc1_v1 = {
        "numeroProcesso": CNJ_REF,
        "grau": "G1",
        "dataHoraUltimaAtualizacao": "2026-11-09T10:00:00.000Z",
    }
    doc2 = {
        "numeroProcesso": cnj2,
        "grau": "G1",
        "dataHoraUltimaAtualizacao": "2026-11-09T11:00:00.000Z",
    }

    # Day 1 index
    total_1 = update_resolution_index(
        index_file, [doc1_v1, doc2], "tjro_2026-11-09.zip", tribunal="tjro"
    )
    assert total_1 == 2
    assert index_file.exists()

    # Day 2: doc1 updated with newer timestamp
    doc1_v2 = {
        "numeroProcesso": CNJ_REF,
        "grau": "G1",
        "dataHoraUltimaAtualizacao": "2026-11-10T15:00:00.000Z",
    }
    total_2 = update_resolution_index(index_file, [doc1_v2], "tjro_2026-11-10.zip", tribunal="tjro")
    assert total_2 == 2

    # Verify pointer
    table = pq.read_table(index_file)
    rows = table.to_pylist()
    cnj1_row = next(r for r in rows if r["numero_processo"] == CNJ_REF)
    assert cnj1_row["zip_file"] == "tjro_2026-11-10.zip"
    assert cnj1_row["data_hora_ultima_atualizacao"] == "2026-11-10T15:00:00.000Z"

    cnj2_row = next(r for r in rows if r["numero_processo"] == cnj2)
    assert cnj2_row["zip_file"] == "tjro_2026-11-09.zip"
