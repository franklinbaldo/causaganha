"""Bounded JURIS/STJ content search normalizes results without hiding provenance."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from causaganha.decisoes.planner import DecisionSearchPlan
from causaganha.decisoes.published import PublishedDecisionDataset
from causaganha.decisoes.search import search_decisions


def _write_juris(path: Path) -> None:
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE juris AS SELECT
                'j1'::VARCHAR AS id_documento,
                '0000001-02.2024.8.22.0001'::VARCHAR AS nr_processo,
                DATE '2026-02-10' AS data_julgamento,
                'ACÓRDÃO'::VARCHAR AS tipo,
                '2ª Câmara'::VARCHAR AS orgao,
                'Des. Exemplo'::VARCHAR AS relator,
                'Apelação'::VARCHAR AS classe_judicial,
                'Responsabilidade civil e dano moral reconhecido.'::VARCHAR AS texto_limpo,
                'https://juris.example/j1'::VARCHAR AS url_portal
            """
        )
        con.execute("COPY juris TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()


def _write_stj(path: Path) -> None:
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE stj AS SELECT
                's1'::VARCHAR AS id,
                '00000010220248220001'::VARCHAR AS "numeroProcesso",
                DATE '2026-03-15' AS "dataDecisao",
                'REsp'::VARCHAR AS "siglaClasse",
                'MIN. EXEMPLO'::VARCHAR AS "ministroRelator",
                'Responsabilidade civil'::VARCHAR AS "tema",
                'Há dever de indenizar.'::VARCHAR AS "teseJuridica",
                'Recurso especial. Dano moral. Responsabilidade civil.'::VARCHAR AS "ementa"
            """
        )
        con.execute("COPY stj TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()


def _write_stj_multi(path: Path) -> None:
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE stj AS
            SELECT * FROM (VALUES
                ('s1', '00000010220248220001', DATE '2026-03-15', 'REsp',
                 'MIN. EXEMPLO', 'Responsabilidade civil', 'Há dever de indenizar.',
                 'Recurso especial. Dano moral. Responsabilidade civil um.'),
                ('s2', '00000020220248220001', DATE '2026-03-14', 'REsp',
                 'MIN. EXEMPLO', 'Responsabilidade civil', 'Há dever de indenizar.',
                 'Recurso especial. Dano moral. Responsabilidade civil dois.'),
                ('s3', '00000030220248220001', DATE '2026-03-13', 'REsp',
                 'MIN. EXEMPLO', 'Responsabilidade civil', 'Há dever de indenizar.',
                 'Recurso especial. Dano moral. Responsabilidade civil três.')
            ) AS t(id, "numeroProcesso", "dataDecisao", "siglaClasse",
                   "ministroRelator", "tema", "teseJuridica", "ementa")
            """
        )
        con.execute("COPY stj TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()


def _plan(juris: Path, stj: Path) -> DecisionSearchPlan:
    return DecisionSearchPlan(
        juris=(
            PublishedDecisionDataset(
                fonte="juris",
                url=str(juris),
                periodo="2026-02",
            ),
        ),
        stj=(PublishedDecisionDataset(fonte="stj", url=str(stj)),),
        data_inicio=date(2026, 1, 1),
        data_fim=date(2026, 4, 1),
    )


def test_search_normalizes_both_sources_and_keeps_provenance(tmp_path: Path) -> None:
    juris = tmp_path / "juris.parquet"
    stj = tmp_path / "stj.parquet"
    _write_juris(juris)
    _write_stj(stj)

    result = search_decisions("responsabilidade civil", _plan(juris, stj))

    assert [item.fonte for item in result.resultados] == ["stj", "juris"]
    assert all(item.natureza == "teor" for item in result.resultados)
    assert result.resultados[0].id_documento == "s1"
    assert result.resultados[1].url == "https://juris.example/j1"
    assert result.datasets_consultados == 2
    assert result.limitacoes == []


def test_source_failure_is_reported_without_erasing_other_source(tmp_path: Path) -> None:
    stj = tmp_path / "stj.parquet"
    _write_stj(stj)
    missing = tmp_path / "missing-juris.parquet"

    result = search_decisions("dano moral", _plan(missing, stj))

    assert [item.fonte for item in result.resultados] == ["stj"]
    assert len(result.limitacoes) == 1
    assert "juris" in result.limitacoes[0]


def test_date_filter_and_global_limit_are_explicit(tmp_path: Path) -> None:
    juris = tmp_path / "juris.parquet"
    stj = tmp_path / "stj.parquet"
    _write_juris(juris)
    _write_stj(stj)
    plan = DecisionSearchPlan(
        juris=_plan(juris, stj).juris,
        stj=_plan(juris, stj).stj,
        data_inicio=date(2026, 3, 1),
        data_fim=date(2026, 3, 31),
    )

    result = search_decisions("responsabilidade civil", plan, limite=1)

    assert [item.fonte for item in result.resultados] == ["stj"]
    assert result.resultados_truncados is False


def test_invalid_text_and_limit_fail_before_query() -> None:
    empty = DecisionSearchPlan(juris=(), stj=(), data_inicio=None, data_fim=None)

    for texto in ("", " ", "x"):
        with pytest.raises(ValueError, match="2 caracteres"):
            search_decisions(texto, empty)

    with pytest.raises(ValueError, match="1 e 100"):
        search_decisions("ok", empty, limite=0)


def test_neither_texto_nor_cnj_is_rejected_before_query() -> None:
    empty = DecisionSearchPlan(juris=(), stj=(), data_inicio=None, data_fim=None)

    with pytest.raises(ValueError, match="cnj"):
        search_decisions(None, empty)


def test_cnj_lookup_matches_exact_process_across_sources_without_texto(
    tmp_path: Path,
) -> None:
    juris = tmp_path / "juris.parquet"
    stj = tmp_path / "stj.parquet"
    _write_juris(juris)
    _write_stj(stj)
    plan = DecisionSearchPlan(
        juris=(PublishedDecisionDataset(fonte="juris", url=str(juris), periodo="2026-02"),),
        stj=(PublishedDecisionDataset(fonte="stj", url=str(stj)),),
        data_inicio=None,
        data_fim=None,
    )

    result = search_decisions(None, plan, cnj="00000010220248220001")

    assert {item.fonte for item in result.resultados} == {"juris", "stj"}
    assert all(item.cnj == "00000010220248220001" for item in result.resultados)
    assert result.limitacoes == []


def test_offset_pages_through_globally_sorted_results(tmp_path: Path) -> None:
    stj = tmp_path / "stj.parquet"
    _write_stj_multi(stj)
    plan = DecisionSearchPlan(
        juris=(),
        stj=(PublishedDecisionDataset(fonte="stj", url=str(stj)),),
        data_inicio=None,
        data_fim=None,
    )

    page1 = search_decisions("responsabilidade civil", plan, limite=1, offset=0)
    page2 = search_decisions("responsabilidade civil", plan, limite=1, offset=1)
    page3 = search_decisions("responsabilidade civil", plan, limite=1, offset=2)
    page4 = search_decisions("responsabilidade civil", plan, limite=1, offset=3)

    assert [item.id_documento for item in page1.resultados] == ["s1"]
    assert page1.resultados_truncados is True
    assert [item.id_documento for item in page2.resultados] == ["s2"]
    assert page2.resultados_truncados is True
    assert [item.id_documento for item in page3.resultados] == ["s3"]
    assert page3.resultados_truncados is False
    assert page4.resultados == []
    assert page4.resultados_truncados is False


def test_negative_offset_is_rejected_before_query() -> None:
    empty = DecisionSearchPlan(juris=(), stj=(), data_inicio=None, data_fim=None)

    with pytest.raises(ValueError, match="offset"):
        search_decisions("ok", empty, offset=-1)


def test_offset_beyond_budget_is_rejected_before_query() -> None:
    empty = DecisionSearchPlan(juris=(), stj=(), data_inicio=None, data_fim=None)

    with pytest.raises(ValueError, match="offset"):
        search_decisions("ok", empty, limite=100, offset=500)


def test_cnj_lookup_can_combine_with_texto_as_additional_filter(tmp_path: Path) -> None:
    juris = tmp_path / "juris.parquet"
    _write_juris(juris)
    plan = DecisionSearchPlan(
        juris=(PublishedDecisionDataset(fonte="juris", url=str(juris), periodo="2026-02"),),
        stj=(),
        data_inicio=None,
        data_fim=None,
    )

    matched = search_decisions("responsabilidade civil", plan, cnj="00000010220248220001")
    unmatched = search_decisions("responsabilidade civil", plan, cnj="99999999999999999999")

    assert [item.fonte for item in matched.resultados] == ["juris"]
    assert unmatched.resultados == []
