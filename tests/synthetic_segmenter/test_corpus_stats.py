"""Tests for scripts.synthetic_segmenter.corpus_stats.

Uses ``ibis.memtable`` — no parquet file or network needed, matching the
module's "takes an already-connected ibis.Table" design (production
callers use ``con.read_parquet(...)`` instead).
"""

from __future__ import annotations

import ibis

from scripts.synthetic_segmenter.corpus_stats import compute_structural_stats


def _table(rows: list[dict]) -> ibis.Table:
    return ibis.memtable(rows)


def test_empty_table_returns_zero_total() -> None:
    empty = _table([{"id": "x", "texto": "placeholder"}])
    table = empty.filter(empty.id == "no-such-id")
    stats = compute_structural_stats(table)
    assert stats["total_documents"] == 0


def test_length_stats_computed() -> None:
    table = _table(
        [
            {"id": "a", "texto": "a" * 10},
            {"id": "b", "texto": "b" * 20},
            {"id": "c", "texto": "c" * 30},
        ]
    )
    stats = compute_structural_stats(table)
    assert stats["total_documents"] == 3
    assert stats["length"]["min"] == 10
    assert stats["length"]["max"] == 30
    assert stats["length"]["mean"] == 20.0


def test_section_presence_rate_counts_documents_with_the_phrase() -> None:
    table = _table(
        [
            {"id": "a", "texto": "RELATÓRIO. Trata-se de uma ação. É o relatório."},
            {"id": "b", "texto": "Documento sem seção de relatório nenhuma."},
        ]
    )
    stats = compute_structural_stats(table)
    assert stats["section_presence_rate"]["relatorio"] == 0.5


def test_section_presence_rate_all_present() -> None:
    table = _table(
        [
            {"id": "a", "texto": "PODER JUDICIÁRIO do Estado."},
            {"id": "b", "texto": "PODER JUDICIÁRIO em outro caso."},
        ]
    )
    stats = compute_structural_stats(table)
    assert stats["section_presence_rate"]["cabecalho"] == 1.0


def test_section_presence_rate_none_present() -> None:
    table = _table([{"id": "a", "texto": "totalmente irrelevante"}])
    stats = compute_structural_stats(table)
    assert stats["section_presence_rate"]["voto"] == 0.0


def test_all_metrics_computed_together_do_not_cross_contaminate() -> None:
    # Every metric (length stats + each PAIR_PHRASES base's presence rate)
    # is now fused into a single aggregate() call -- this guards against a
    # fusion bug where one base's boolean expression leaks into another's
    # sum, or the length aggregate picks up the wrong column.
    texto_a = "PODER JUDICIÁRIO. " + "x" * 50
    texto_b = "RELATÓRIO. Trata-se de uma ação. É o relatório." + "y" * 10
    texto_c = "nada de especial aqui"
    table = _table(
        [
            {"id": "a", "texto": texto_a},
            {"id": "b", "texto": texto_b},
            {"id": "c", "texto": texto_c},
        ]
    )
    stats = compute_structural_stats(table)
    assert stats["total_documents"] == 3
    assert stats["section_presence_rate"]["cabecalho"] == 1 / 3
    assert stats["section_presence_rate"]["relatorio"] == 1 / 3
    assert stats["section_presence_rate"]["voto"] == 0.0
    assert stats["length"]["min"] == len(texto_c)
    assert stats["length"]["max"] == len(texto_a)
