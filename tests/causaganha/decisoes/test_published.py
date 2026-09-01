"""Published decision-dataset discovery is manifest-driven and deterministic."""

from __future__ import annotations

from causaganha.decisoes.published import (
    STJ_PARQUET_URL,
    discover_published_decision_datasets,
    discover_published_juris_datasets,
)


MANIFEST = """tipo,mes_ano,ia_status,n_docs,updated_at
ACÓRDÃO,2026-06,uploaded,5,2026-07-01T00:00:00+00:00
DECISÃO / MONOCRÁTICA,2026-07,uploaded,2,2026-08-01T00:00:00+00:00
EMENTA,2026-08,,10,2026-09-01T00:00:00+00:00
VOTO,2026-09,uploaded,0,2026-09-02T00:00:00+00:00
"""


def test_juris_discovery_only_exposes_uploaded_nonempty_windows() -> None:
    datasets = discover_published_juris_datasets(MANIFEST)

    assert [(item.periodo, item.tipo, item.registros) for item in datasets] == [
        ("2026-06", "ACÓRDÃO", 5),
        ("2026-07", "DECISÃO / MONOCRÁTICA", 2),
    ]
    assert datasets[0].url == (
        "https://archive.org/download/tjro-juris-2026/2026-06-AC%C3%93RD%C3%83O.parquet"
    )
    assert datasets[1].url.endswith("/2026-07-DECIS%C3%83O___MONOCR%C3%81TICA.parquet")


def test_combined_discovery_keeps_stj_as_distinct_source() -> None:
    datasets = discover_published_decision_datasets(MANIFEST)

    assert [item.fonte for item in datasets] == ["juris", "juris", "stj"]
    assert datasets[-1].url == STJ_PARQUET_URL
    assert datasets[-1].periodo is None
