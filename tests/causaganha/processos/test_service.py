"""Tests for causaganha.processos.service.buscar_processo (RFC 0014 M2).

Fixtures are hand-built local parquets wired together through a small
indice_processual.parquet whose `arquivo_ia_url` column points at those local
paths — DuckDB's `read_parquet()` accepts local paths exactly like it accepts
IA URLs, so this exercises the same SQL the real service runs against remote
parquets, without any network access.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import duckdb
import pytest

from causaganha.processos import service
from causaganha.processos.models import CnjInvalidoError


if TYPE_CHECKING:
    from pathlib import Path

CNJ_ALL = "00000010220248220001"
CNJ_DJEN_ONLY = "00000020320248220002"
CNJ_UNKNOWN = "00000030420248220003"

# Matches fixtures["report"]'s generated_at below — used to keep the
# "avisos == []" assertions deterministic instead of drifting with wall
# clock time (the fixture's fixed timestamp will eventually be more than
# 48h in the real past).
GERADO_EM = datetime(2026, 7, 12, 18, 0, 0, tzinfo=UTC)


def _copy_to_parquet(path: Path, sql: str) -> Path:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


@pytest.fixture
def fixtures(tmp_path: Path) -> dict[str, Path]:
    comunicacoes = _copy_to_parquet(
        tmp_path / "comunicacoes.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}',       DATE '2024-03-01', 'TJRO'),
            ('{CNJ_ALL}',       DATE '2024-03-05', 'TJRO'),
            ('{CNJ_DJEN_ONLY}', DATE '2024-04-01', 'TJRO')
        ) AS t(numero_processo, data_disponibilizacao, tribunal)
        """,
    )
    juris = _copy_to_parquet(
        tmp_path / "tjro-juris-2024.parquet",
        f"""
        SELECT * FROM (VALUES
            (1, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A',
             DATE '2024-01-15', 'texto um', 'https://juris/1')
        ) AS t(id_documento, nr_processo, tipo, classe_judicial, orgao, relator,
               data_julgamento, texto_limpo, url_portal)
        """,
    )
    stj = _copy_to_parquet(
        tmp_path / "stj-acordaos.parquet",
        f"""
        SELECT * FROM (VALUES
            ('stj-1', '{CNJ_ALL}', 'REsp', 'MIN X', 'tema', 'tese', 'ementa',
             DATE '2024-05-01', DATE '2024-05-10')
        ) AS t(id, "numeroProcesso", "siglaClasse", "ministroRelator", tema,
               "teseJuridica", ementa, "dataDecisao", "dataPublicacao")
        """,
    )
    datajud = _copy_to_parquet(
        tmp_path / "datajud-capa-tjro.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}', 'Apelacao Civel', 'Contratos', '2a Camara', 'G2',
             DATE '2024-01-10', TIMESTAMP '2024-06-01 00:00:00')
        ) AS t(numero_processo, classe_nome, assuntos, orgao_julgador, grau,
               data_ajuizamento, ultima_atualizacao)
        """,
    )
    indice = _copy_to_parquet(
        tmp_path / "indice_processual.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}',       'djen',    'c1',    'TJRO', DATE '2024-03-01', '{comunicacoes}'),
            ('{CNJ_ALL}',       'djen',    'c2',    'TJRO', DATE '2024-03-05', '{comunicacoes}'),
            ('{CNJ_ALL}',       'juris',   '1',     'TJRO', DATE '2024-01-15', '{juris}'),
            ('{CNJ_ALL}',       'stj',     'stj-1', 'STJ',  DATE '2024-05-01', '{stj}'),
            ('{CNJ_ALL}',       'datajud', 'dj-1',  'TJRO', DATE '2024-06-01', '{datajud}'),
            ('{CNJ_DJEN_ONLY}', 'djen',    'c3',    'TJRO', DATE '2024-04-01', '{comunicacoes}')
        ) AS t(numero_processo, fonte, registro_id, tribunal, data, arquivo_ia_url)
        """,
    )
    report = tmp_path / "indice_processual.report.json"
    report.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-12T18:00:00Z",
                "sources": {
                    "djen": {"status": "loaded_remote", "rows": 2},
                    "juris": {"status": "loaded_remote", "rows": 1},
                    "stj": {"status": "loaded_remote", "rows": 1},
                    "datajud": {"status": "loaded_remote", "rows": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "indice": indice,
        "report": report,
        "comunicacoes": comunicacoes,
        "juris": juris,
        "stj": stj,
        "datajud": datajud,
    }


def test_multi_fonte_dossier(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=GERADO_EM,
    )

    assert result.encontrado is True
    assert result.nr_processo == CNJ_ALL
    assert result.nr_processo_mascara == "0000001-02.2024.8.22.0001"
    assert result.fontes_presentes == ["datajud", "djen", "juris", "stj"]
    assert result.avisos == []
    assert result.dataset_gerado_em == "2026-07-12T18:00:00Z"

    assert result.djen.n_publicacoes == 2
    assert result.djen.primeira_publicacao == "2024-03-01"
    assert result.djen.ultima_publicacao == "2024-03-05"
    assert result.djen.tribunais == ["TJRO"]

    assert result.juris.n_documentos == 1
    assert result.juris.orgao == "2a Camara"
    assert result.juris.relator == "Des. A"
    assert result.juris.url == "https://juris/1"

    assert result.stj.id == "stj-1"
    assert result.stj.classe == "REsp"
    assert result.stj.data_decisao == "2024-05-01"

    assert result.datajud.classe_oficial == "Apelacao Civel"
    assert result.datajud.assuntos == "Contratos"

    assert [d.fonte for d in result.documentos] == ["stj", "juris"]  # data DESC
    assert result.documentos_truncados is False


def test_single_fonte_dossier_leaves_other_fields_none(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_DJEN_ONLY, indice_url=str(fixtures["indice"]), report_url=str(fixtures["report"])
    )

    assert result.encontrado is True
    assert result.fontes_presentes == ["djen"]
    assert result.djen is not None
    assert result.juris is None
    assert result.stj is None
    assert result.datajud is None
    assert result.documentos == []
    assert result.documentos_truncados is False


def test_not_found_still_carries_cobertura(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_UNKNOWN,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=GERADO_EM,
    )

    assert result.encontrado is False
    assert result.nr_processo == CNJ_UNKNOWN
    assert result.fontes_presentes == []
    assert result.dataset_gerado_em == "2026-07-12T18:00:00Z"
    assert {c.fonte for c in result.cobertura_dataset} == {"djen", "juris", "stj", "datajud"}
    assert result.avisos == []


def test_fresh_snapshot_has_no_staleness_aviso(fixtures: dict[str, Path]) -> None:
    """dataset_gerado_em within the 48h SLO (docs/SERVICE_OBJECTIVES.md) is silent."""
    quase_48h_depois = GERADO_EM + timedelta(hours=47)
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=quase_48h_depois,
    )

    assert result.avisos == []


def test_stale_snapshot_warns_and_points_to_live_state(fixtures: dict[str, Path]) -> None:
    """A snapshot far older than the 48h SLO must not silently look current.

    Mirrors issue #891's staleness rule: "não confundir 'o processo parou'
    com 'a cópia parou'" — an old dataset_gerado_em must surface as an
    explicit warning pointing at the live-state route, not be silent.
    """
    tres_dias_depois = GERADO_EM + timedelta(days=3)
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=tres_dias_depois,
    )

    assert len(result.avisos) == 1
    aviso = result.avisos[0]
    assert "48" in aviso
    assert "processo_estado" in aviso


def test_stale_snapshot_also_warns_when_processo_not_found(fixtures: dict[str, Path]) -> None:
    """Staleness is a property of the snapshot, independent of this CNJ's hit/miss."""
    tres_dias_depois = GERADO_EM + timedelta(days=3)
    result = service.buscar_processo(
        CNJ_UNKNOWN,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=tres_dias_depois,
    )

    assert result.encontrado is False
    assert any("processo_estado" in a for a in result.avisos)


def test_missing_report_has_no_staleness_aviso_beyond_its_own(
    fixtures: dict[str, Path],
) -> None:
    """No dataset_gerado_em to compare against — never fabricate a staleness claim."""
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["indice"].parent / "does-not-exist.report.json"),
    )

    assert result.avisos == [service._RELATORIO_INDISPONIVEL_AVISO]


def test_invalid_cnj_raises_before_touching_any_parquet() -> None:
    with pytest.raises(CnjInvalidoError):
        service.buscar_processo(
            "123",
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.json",
        )


def test_missing_report_is_partial_not_fatal(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["indice"].parent / "does-not-exist.report.json"),
    )

    assert result.encontrado is True  # the processo itself still resolves
    assert result.cobertura_dataset == []
    assert result.dataset_gerado_em is None
    assert any("relatório de cobertura" in a.lower() for a in result.avisos)


def test_one_source_parquet_unreachable_is_partial_not_fatal(
    fixtures: dict[str, Path], tmp_path: Path
) -> None:
    """A source's own parquet failing must not take down the whole dossiê.

    Mirrors reconcile_processos.py's own philosophy (a corrupted/unreachable
    source parquet degrades to a warning, never crashes the run) — the
    module docstring promises the same for buscar_processo, exercised here
    against DJEN specifically (its arquivo_ia_url points nowhere).
    """
    missing = tmp_path / "missing.parquet"
    broken_indice = _copy_to_parquet(
        tmp_path / "indice_broken.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}', 'djen',    'c1',    'TJRO', DATE '2024-03-01', '{missing}'),
            ('{CNJ_ALL}', 'juris',   '1',     'TJRO', DATE '2024-01-15', '{fixtures["juris"]}'),
            ('{CNJ_ALL}', 'stj',     'stj-1', 'STJ',  DATE '2024-05-01', '{fixtures["stj"]}'),
            ('{CNJ_ALL}', 'datajud', 'dj-1',  'TJRO', DATE '2024-06-01', '{fixtures["datajud"]}')
        ) AS t(numero_processo, fonte, registro_id, tribunal, data, arquivo_ia_url)
        """,
    )

    result = service.buscar_processo(
        CNJ_ALL, indice_url=str(broken_indice), report_url=str(fixtures["report"])
    )

    assert result.encontrado is True
    assert result.djen is None  # the broken source's gap is empty, not a crash
    assert any("djen" in a.lower() for a in result.avisos)
    # unaffected sources still load normally
    assert result.juris is not None
    assert result.stj is not None
    assert result.datajud is not None


def test_indice_processual_itself_unreachable_propagates() -> None:
    """Unlike a source parquet, the index itself failing has no partial answer."""
    with pytest.raises(duckdb.Error):
        service.buscar_processo(
            CNJ_ALL,
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.report.json",
        )


def test_incluir_documentos_false_skips_the_documentos_query(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        incluir_documentos=False,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
    )

    assert result.documentos == []
    assert result.documentos_truncados is False
    # the per-fonte summaries are unaffected — only the documents list is skipped
    assert result.juris is not None
    assert result.stj is not None


def test_limite_documentos_truncates_and_flags_it(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        limite_documentos=1,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
    )

    assert len(result.documentos) == 1
    assert result.documentos[0].fonte == "stj"  # most recent by data DESC
    assert result.documentos_truncados is True


def _spy_on_connect(monkeypatch: pytest.MonkeyPatch) -> list[duckdb.DuckDBPyConnection]:
    """Wraps duckdb.connect so the test can inspect the connection afterwards."""
    captured: list[duckdb.DuckDBPyConnection] = []
    real_connect = duckdb.connect

    def _spy(*args: object, **kwargs: object) -> duckdb.DuckDBPyConnection:
        con = real_connect(*args, **kwargs)
        captured.append(con)
        return con

    monkeypatch.setattr(service.duckdb, "connect", _spy)
    return captured


def test_connection_is_closed_on_success(
    fixtures: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A long-running MCP server calls buscar_processo repeatedly — a leaked
    DuckDBPyConnection per call would accumulate handles/memory over time.
    """
    captured = _spy_on_connect(monkeypatch)

    service.buscar_processo(
        CNJ_ALL, indice_url=str(fixtures["indice"]), report_url=str(fixtures["report"])
    )

    assert len(captured) == 1
    with pytest.raises(duckdb.Error):
        captured[0].execute("SELECT 1")  # closed connections refuse queries


def test_connection_is_closed_when_indice_itself_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one fatal path (index unreachable) must still close the connection."""
    captured = _spy_on_connect(monkeypatch)

    with pytest.raises(duckdb.Error):
        service.buscar_processo(
            CNJ_ALL,
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.report.json",
        )

    assert len(captured) == 1
    with pytest.raises(duckdb.Error):
        captured[0].execute("SELECT 1")
