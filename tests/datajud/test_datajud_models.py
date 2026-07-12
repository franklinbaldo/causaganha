"""Tests for datajud.models — 14-digit date normalization and capa parsing."""

from __future__ import annotations

from datajud.models import (
    ProcessoCapa,
    data14_bound,
    formatar_cnj,
    normalizar_cnj,
    normalizar_data14,
)


CNJ = "00000010220248220001"

SOURCE_G1 = {
    "numeroProcesso": CNJ,
    "tribunal": "TJRO",
    "grau": "G1",
    "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
    "assuntos": [
        {"codigo": 1234, "nome": "Dano Material"},
        {"codigo": 5678, "nome": "Dano Moral"},
        {"codigo": 1234, "nome": "Dano Material"},  # duplicate name
    ],
    "orgaoJulgador": {"codigo": 111, "nome": "1ª Vara Cível"},
    "sistema": {"codigo": 1, "nome": "PJE"},
    "formato": {"codigo": 1, "nome": "Eletrônico"},
    "nivelSigilo": 0,
    "dataAjuizamento": "20240115103000",
    "dataHoraUltimaAtualizacao": "2026-06-13T09:45:09.000Z",
    "movimentos": [
        {
            "codigo": 26,
            "nome": "Distribuição",
            "dataHora": "2024-01-15T10:30:00.000Z",
            "complementosTabelados": [
                {"codigo": 2, "descricao": "tipo_de_distribuicao", "nome": "sorteio", "valor": 2}
            ],
        },
        {"codigo": 51, "nome": "Audiência", "dataHora": "2024-03-01T14:00:00.000Z"},
    ],
}


# ── 14-digit date normalization ──────────────────────────────────────────


def test_normalizar_data14_full_timestamp():
    assert normalizar_data14("20240115103000") == "2024-01-15T10:30:00"


def test_normalizar_data14_date_only_pads_time():
    assert normalizar_data14("20240115") == "2024-01-15T00:00:00"


def test_normalizar_data14_partial_time():
    assert normalizar_data14("202401151030") == "2024-01-15T10:30:00"


def test_normalizar_data14_invalid_returns_none():
    assert normalizar_data14("") is None
    assert normalizar_data14(None) is None
    assert normalizar_data14("not-a-date") is None


def test_data14_bound_covers_the_whole_day():
    assert data14_bound("15/01/2024") == "20240115000000"
    assert data14_bound("15/01/2024", fim=True) == "20240115235959"
    assert data14_bound("2024-01-15") == "20240115000000"
    assert data14_bound("2024-01-15", fim=True) == "20240115235959"


# ── CNJ helpers ──────────────────────────────────────────────────────────


def test_normalizar_cnj_strips_mask():
    assert normalizar_cnj("0000001-02.2024.8.22.0001") == CNJ
    assert normalizar_cnj("6081") == ""
    assert normalizar_cnj(None) == ""


def test_formatar_cnj_roundtrip():
    assert formatar_cnj(CNJ) == "0000001-02.2024.8.22.0001"
    assert formatar_cnj("123") == "123"


# ── Capa parsing ─────────────────────────────────────────────────────────


def test_from_source_parses_capa_and_movimentos():
    capa = ProcessoCapa.from_source(SOURCE_G1)
    assert capa.cnj == CNJ
    assert capa.grau == "G1"
    assert capa.classe.codigo == 7
    assert capa.orgao_julgador.codigo == 111
    assert len(capa.movimentos) == 2
    assert capa.movimentos[0].complementos_str() == "tipo_de_distribuicao=sorteio"
    assert capa.dedup_key() == (CNJ, "G1", 111)


def test_assuntos_str_dedupes_preserving_order():
    capa = ProcessoCapa.from_source(SOURCE_G1)
    assert capa.assuntos_str() == "Dano Material; Dano Moral"


def test_from_source_tolerates_null_and_nested_assuntos():
    source = dict(SOURCE_G1, assuntos=None, movimentos=None)
    capa = ProcessoCapa.from_source(source)
    assert capa.assuntos == []
    assert capa.movimentos == []

    nested = dict(SOURCE_G1, assuntos=[[{"codigo": 1, "nome": "Nested"}]])
    assert ProcessoCapa.from_source(nested).assuntos_str() == "Nested"


def test_capa_row_normalizes_the_14_digit_date():
    capa = ProcessoCapa.from_source(SOURCE_G1)
    row = capa.capa_row(tribunal="tjro", consultado_em="2026-07-07T00:00:00+00:00")
    assert row["data_ajuizamento"] == "2024-01-15T10:30:00"
    assert row["numero_processo"] == CNJ
    assert row["tribunal"] == "TJRO"
    assert row["assuntos"] == "Dano Material; Dano Moral"
    assert row["n_movimentos"] == 2
    assert row["ultima_atualizacao"] == "2026-06-13T09:45:09.000Z"


def test_capa_row_falls_back_to_cli_tribunal():
    source = dict(SOURCE_G1)
    source.pop("tribunal")
    row = ProcessoCapa.from_source(source).capa_row(tribunal="tjro", consultado_em="x")
    assert row["tribunal"] == "TJRO"


def test_movimento_rows_flatten_the_line():
    capa = ProcessoCapa.from_source(SOURCE_G1)
    rows = capa.movimento_rows(tribunal="tjro")
    assert len(rows) == 2
    assert rows[0]["numero_processo"] == CNJ
    assert rows[0]["grau"] == "G1"
    assert rows[0]["orgao_julgador_codigo"] == 111
    assert rows[0]["codigo"] == 26
    assert rows[0]["complementos"] == "tipo_de_distribuicao=sorteio"
    assert rows[1]["complementos"] == ""
