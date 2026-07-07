"""Tests for datajud.dedup — multi-grau natural key, latest update wins."""

from __future__ import annotations

from datajud.dedup import dedup_capas, merge_capa_rows, merge_movimento_rows
from datajud.models import ProcessoCapa


CNJ = "00000010220248220001"


def _capa(grau: str, orgao: int, atualizacao: str, classe: str = "AC") -> ProcessoCapa:
    return ProcessoCapa.from_source(
        {
            "numeroProcesso": CNJ,
            "tribunal": "TJRO",
            "grau": grau,
            "classe": {"codigo": 1, "nome": classe},
            "orgaoJulgador": {"codigo": orgao, "nome": f"Órgão {orgao}"},
            "dataHoraUltimaAtualizacao": atualizacao,
        }
    )


# ── dedup_capas ──────────────────────────────────────────────────────────


def test_multi_grau_documents_of_same_cnj_are_all_kept():
    """G1 and G2 of the same CNJ are distinct documents — never collapsed."""
    g1 = _capa("G1", 111, "2026-01-01T00:00:00Z")
    g2 = _capa("G2", 222, "2026-01-02T00:00:00Z")
    result = dedup_capas([g1, g2])
    assert len(result) == 2
    assert {c.grau for c in result} == {"G1", "G2"}


def test_same_key_latest_ultima_atualizacao_wins():
    old = _capa("G1", 111, "2025-01-01T00:00:00Z", classe="old")
    new = _capa("G1", 111, "2026-01-01T00:00:00Z", classe="new")
    result = dedup_capas([new, old])  # order must not matter
    assert len(result) == 1
    assert result[0].classe.nome == "new"


def test_same_key_tie_keeps_the_later_occurrence():
    first = _capa("G1", 111, "2026-01-01T00:00:00Z", classe="first")
    second = _capa("G1", 111, "2026-01-01T00:00:00Z", classe="second")
    result = dedup_capas([first, second])
    assert len(result) == 1
    assert result[0].classe.nome == "second"


def test_missing_ultima_atualizacao_loses_to_dated_version():
    undated = _capa("G1", 111, "", classe="undated")
    undated.data_hora_ultima_atualizacao = None
    dated = _capa("G1", 111, "2026-01-01T00:00:00Z", classe="dated")
    result = dedup_capas([dated, undated])
    assert result[0].classe.nome == "dated"


def test_different_orgao_same_grau_are_distinct_documents():
    a = _capa("G1", 111, "2026-01-01T00:00:00Z")
    b = _capa("G1", 999, "2026-01-01T00:00:00Z")
    assert len(dedup_capas([a, b])) == 2


# ── merge_capa_rows (incremental re-runs) ────────────────────────────────


def _row(grau: str, orgao: int, atualizacao: str, marker: str) -> dict:
    return {
        "numero_processo": CNJ,
        "grau": grau,
        "orgao_julgador_codigo": orgao,
        "ultima_atualizacao": atualizacao,
        "classe_nome": marker,
    }


def test_merge_capa_rows_new_version_replaces_old():
    existing = [_row("G1", 111, "2025-01-01T00:00:00Z", "old")]
    new = [_row("G1", 111, "2026-01-01T00:00:00Z", "new")]
    merged = merge_capa_rows(existing, new)
    assert len(merged) == 1
    assert merged[0]["classe_nome"] == "new"


def test_merge_capa_rows_tie_prefers_the_fresh_fetch():
    existing = [_row("G1", 111, "2026-01-01T00:00:00Z", "old")]
    new = [_row("G1", 111, "2026-01-01T00:00:00Z", "new")]
    assert merge_capa_rows(existing, new)[0]["classe_nome"] == "new"


def test_merge_capa_rows_keeps_untouched_documents():
    existing = [_row("G1", 111, "2025-01-01T00:00:00Z", "keep")]
    new = [_row("G2", 222, "2026-01-01T00:00:00Z", "new")]
    merged = merge_capa_rows(existing, new)
    assert len(merged) == 2
    assert {r["classe_nome"] for r in merged} == {"keep", "new"}


# ── merge_movimento_rows ─────────────────────────────────────────────────


def _mov(grau: str, orgao: int, codigo: int) -> dict:
    return {
        "numero_processo": CNJ,
        "grau": grau,
        "orgao_julgador_codigo": orgao,
        "codigo": codigo,
        "data_hora": f"2026-01-0{codigo}T00:00:00Z",
    }


def test_merge_movimentos_replaces_refreshed_documents_wholesale():
    existing = [_mov("G1", 111, 1), _mov("G1", 111, 2), _mov("G2", 222, 3)]
    new = [_mov("G1", 111, 9)]
    merged = merge_movimento_rows(existing, new, {(CNJ, "G1", 111)})
    codigos = sorted(r["codigo"] for r in merged)
    assert codigos == [3, 9]  # old G1 rows dropped, G2 kept


def test_merge_movimentos_refreshed_document_with_zero_movements_clears_old():
    existing = [_mov("G1", 111, 1)]
    merged = merge_movimento_rows(existing, [], {(CNJ, "G1", 111)})
    assert merged == []
