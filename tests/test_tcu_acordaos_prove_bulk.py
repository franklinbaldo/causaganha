"""Tests for the pure report-assembly logic of the #984 TCU bulk proof script.

Only ``build_report`` is unit-tested here: it is the one part of
``scripts/tcu_acordaos_prove_bulk.py`` with no network or filesystem I/O. The rest of the
script performs a real download against the official TCU portal and is run manually, once,
to produce ``docs/data/tcu-acordaos-bulk-proof.json``.
"""

from __future__ import annotations

from scripts.tcu_acordaos_prove_bulk import build_report


def test_build_report_flags_compatible_schema_and_totals_history() -> None:
    report = build_report(
        year="1992",
        source_url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-1992.csv",
        final_url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-1992.csv",
        acquired_at="2026-09-02T18:00:00Z",
        size_bytes=15_800_000,
        sha256="a" * 64,
        observed_header=["KEY", "TIPO", "TITULO", "ASSUNTO"],
        record_count=1234,
        total_historical_bytes=9_876_543_210,
        years=["1992", "1993"],
        sample_query="tomada de contas",
        sample_hits=3,
    )

    assert report["year"] == "1992"
    assert report["record_count"] == 1234
    assert report["schema"]["missing_required_columns"] != []
    assert report["schema"]["is_compatible"] is False
    assert report["historical_expansion"] == {
        "years_available": ["1992", "1993"],
        "year_count": 2,
        "total_size_bytes": 9_876_543_210,
    }
    assert report["sample_teor_query"] == {"query": "tomada de contas", "hit_count": 3}


def test_build_report_flags_compatible_schema_when_all_required_columns_present() -> None:
    from tcu_acordaos.ingest import REQUIRED_COLUMNS

    report = build_report(
        year="1992",
        source_url="https://sites.tcu.gov.br/x.csv",
        final_url="https://sites.tcu.gov.br/x.csv",
        acquired_at="2026-09-02T18:00:00Z",
        size_bytes=1,
        sha256="b" * 64,
        observed_header=[*REQUIRED_COLUMNS, "VISAOGERAL"],
        record_count=1,
        total_historical_bytes=1,
        years=["1992"],
        sample_query="x",
        sample_hits=0,
    )

    assert report["schema"]["missing_required_columns"] == []
    assert report["schema"]["extra_observed_columns"] == ["VISAOGERAL"]
    assert report["schema"]["is_compatible"] is True
