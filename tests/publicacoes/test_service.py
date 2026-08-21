"""Behavior tests for archive-first publication search."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from causaganha.publicacoes.models import CriteriosInvalidosError
from causaganha.publicacoes.service import buscar_publicacoes


CNJ = "00000010220248220001"


def _write_parquet(path: Path, columns: str, rows: list[tuple]) -> None:
    con = duckdb.connect()
    try:
        con.execute(f"CREATE TABLE data ({columns})")
        if rows:
            placeholders = ", ".join("?" for _ in rows[0])
            con.executemany(f"INSERT INTO data VALUES ({placeholders})", rows)
        con.execute(f"COPY data TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()


def _fixture_archive(tmp_path: Path, *, include_texts: bool = True) -> tuple[str, str]:
    item = "djen-tjro-2026"
    comunicacoes = tmp_path / "comunicacoes.parquet"
    textos = tmp_path / "textos.parquet"
    advogados = tmp_path / "advogados.parquet"
    comunicacao_advogados = tmp_path / "comunicacao_advogados.parquet"
    destinatarios = tmp_path / "destinatarios.parquet"

    _write_parquet(
        comunicacoes,
        """
        id VARCHAR, original_id VARCHAR, tribunal VARCHAR, numero_processo VARCHAR,
        numero_processo_mascara VARCHAR, data_disponibilizacao DATE,
        tipo_comunicacao VARCHAR, nome_orgao VARCHAR, meio VARCHAR, link VARCHAR,
        tipo_documento VARCHAR, nome_classe VARCHAR, codigo_classe VARCHAR,
        numero_comunicacao VARCHAR, hash VARCHAR, processed_at TIMESTAMP,
        texto_id VARCHAR, p_ano INTEGER, p_mes INTEGER, p_item_ia VARCHAR
        """,
        [
            (
                "c1",
                "orig-1",
                "TJRO",
                CNJ,
                "0000001-02.2024.8.22.0001",
                "2026-08-20",
                "Intimação",
                "1ª Vara",
                "D",
                "https://example.test/1",
                "Intimação",
                "Procedimento Comum Cível",
                "7",
                "101",
                "h1",
                "2026-08-20 12:00:00",
                "t1",
                2026,
                8,
                item,
            ),
            (
                "c2",
                "orig-2",
                "TJRO",
                "00000020320248220001",
                "0000002-03.2024.8.22.0001",
                "2026-08-19",
                "Citação",
                "2ª Vara",
                "D",
                "https://example.test/2",
                "Citação",
                "Execução",
                "8",
                "102",
                "h2",
                "2026-08-19 12:00:00",
                "t2",
                2026,
                8,
                item,
            ),
        ],
    )
    _write_parquet(
        textos,
        "id VARCHAR, texto VARCHAR",
        [("t1", "Intimação do servidor público para manifestação."), ("t2", "Citação comum.")],
    )
    _write_parquet(
        advogados,
        """
        id VARCHAR, original_id VARCHAR, tribunal VARCHAR, nome VARCHAR,
        numero_oab VARCHAR, uf_oab VARCHAR, p_ano INTEGER, p_mes INTEGER, p_item_ia VARCHAR
        """,
        [("a1", "ao1", "TJRO", "Maria Silva", "1234", "RO", 2026, 8, item)],
    )
    _write_parquet(
        comunicacao_advogados,
        "comunicacao_id VARCHAR, tribunal VARCHAR, advogado_id VARCHAR",
        [("c1", "TJRO", "a1")],
    )
    _write_parquet(
        destinatarios,
        """
        comunicacao_id VARCHAR, tribunal VARCHAR, nome VARCHAR, polo VARCHAR,
        parte_id VARCHAR, p_ano INTEGER, p_mes INTEGER, p_item_ia VARCHAR
        """,
        [("c1", "TJRO", "João da Silva", "A", "p1", 2026, 8, item)],
    )

    table_paths = {
        "comunicacoes": comunicacoes,
        "advogados": advogados,
        "comunicacao_advogados": comunicacao_advogados,
        "destinatarios": destinatarios,
    }
    if include_texts:
        table_paths["textos"] = textos

    manifest = tmp_path / "manifest.parquet"
    manifest_rows = [
        (
            None,
            "TJRO",
            "parquet",
            table,
            path.name,
            item,
            str(path),
            "2026-08-21T12:00:00+00:00",
        )
        for table, path in table_paths.items()
    ]
    _write_parquet(
        manifest,
        """
        date VARCHAR, tribunal VARCHAR, file_type VARCHAR, table_name VARCHAR,
        file_name VARCHAR, ia_item VARCHAR, ia_url VARCHAR, created_at VARCHAR
        """,
        manifest_rows,
    )

    backfill = tmp_path / "backfill-needed.parquet"
    _write_parquet(
        backfill,
        "date VARCHAR, tribunal VARCHAR, reason VARCHAR, last_checked VARCHAR",
        [("2026-08-18", "TJRO", "not_collected", "2026-08-21T12:00:00+00:00")],
    )
    return str(manifest), str(backfill)


def test_busca_por_cnj_usa_arquivo_e_qualifica_cobertura(tmp_path: Path) -> None:
    manifest, backfill = _fixture_archive(tmp_path)

    result = buscar_publicacoes(
        processo=CNJ,
        tribunal="tjro",
        manifest_url=manifest,
        backfill_url=backfill,
    )

    assert result.total_encontrado == 1
    assert result.resultados[0].id == "c1"
    assert result.resultados[0].numero_processo == CNJ
    assert result.resultados[0].trecho is None
    assert result.resultados[0].ia_item == "djen-tjro-2026"
    assert result.cobertura.status == "parcial"
    assert result.cobertura.lacunas_conhecidas == 1


def test_busca_por_oab_faz_join_interno_sem_expor_schema(tmp_path: Path) -> None:
    manifest, backfill = _fixture_archive(tmp_path)

    result = buscar_publicacoes(
        oab="RO 1234",
        uf_oab="ro",
        tribunal="TJRO",
        manifest_url=manifest,
        backfill_url=backfill,
    )

    assert result.total_encontrado == 1
    assert result.resultados[0].id == "c1"
    assert result.criterios["oab"] == "RO1234"
    assert result.criterios["uf_oab"] == "RO"


def test_busca_por_texto_retorna_trecho_economico(tmp_path: Path) -> None:
    manifest, backfill = _fixture_archive(tmp_path)

    result = buscar_publicacoes(
        texto="servidor público",
        tribunal="TJRO",
        manifest_url=manifest,
        backfill_url=backfill,
    )

    assert result.total_encontrado == 1
    assert result.resultados[0].id == "c1"
    assert result.resultados[0].trecho is not None
    assert "servidor público" in result.resultados[0].trecho


def test_tabela_necessaria_ausente_vira_cobertura_insuficiente(tmp_path: Path) -> None:
    manifest, backfill = _fixture_archive(tmp_path, include_texts=False)

    result = buscar_publicacoes(
        texto="servidor",
        tribunal="TJRO",
        manifest_url=manifest,
        backfill_url=backfill,
    )

    assert result.total_encontrado == 0
    assert result.cobertura.status == "insuficiente"
    assert "textos" in (result.cobertura.aviso or "")


def test_zero_com_gap_nao_parece_prova_de_ausencia(tmp_path: Path) -> None:
    manifest, backfill = _fixture_archive(tmp_path)

    result = buscar_publicacoes(
        advogado="Pessoa inexistente",
        tribunal="TJRO",
        manifest_url=manifest,
        backfill_url=backfill,
    )

    assert result.total_encontrado == 0
    assert result.cobertura.status == "parcial"
    assert result.cobertura.lacunas_conhecidas == 1


def test_rejeita_consulta_sem_criterio() -> None:
    with pytest.raises(CriteriosInvalidosError, match="ao menos um critério"):
        buscar_publicacoes()
