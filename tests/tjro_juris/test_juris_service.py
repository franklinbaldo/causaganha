"""Tests for tjro_juris.service — row mapping and parquet round-trip.

Covers porting the 9 metadata fields from PR #821 (closed unmerged, kept as
historical source per #1014) onto the current service.py, now that #1017
already lets consolidate_year() union narrow/wide schemas by column name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from tjro_juris.service import _PARQUET_SCHEMA, _rows_to_parquet, _to_row


if TYPE_CHECKING:
    from pathlib import Path


_FULL_CRAWLER_DOC = {
    "id_documento": 42,
    "nr_processo": "00042-11.2024.8.22.0001",
    "tipo": "ACÓRDÃO",
    "classe_judicial": "Apelação Cível",
    "orgao": "1ª Câmara Cível",
    "relator": "Des. Fulano",
    "sistema_origem": "pje2instancia",
    "data_julgamento": "2024-03-15",
    "texto_limpo": "EMENTA: teste",
    "url_portal": "https://juris.tjro.jus.br/jurisprudencia/?id=42",
    "extraido_em": "2026-07-14T00:00:00+00:00",
    "id_processo": 999,
    "cd_assunto_trf": "3372",
    "ds_assunto_trf": "Homicídio Qualificado",
    "cd_classe_judicial": "417",
    "nivel_sigilo_processo": 0,
    "grau_jurisdicao": 2,
    "ds_md5_documento": "abc123",
    "id_orgao_julgador": 22,
    "id_orgao_julgador_colegiado": 12,
}


def test_parquet_schema_has_the_nine_new_fields() -> None:
    names = set(_PARQUET_SCHEMA.names)
    assert {
        "id_processo",
        "cd_assunto_trf",
        "ds_assunto_trf",
        "cd_classe_judicial",
        "nivel_sigilo_processo",
        "grau_jurisdicao",
        "ds_md5_documento",
        "id_orgao_julgador",
        "id_orgao_julgador_colegiado",
    }.issubset(names)


def test_to_row_maps_new_metadata_fields() -> None:
    row = _to_row(_FULL_CRAWLER_DOC)
    assert row["id_processo"] == 999
    assert row["cd_assunto_trf"] == "3372"
    assert row["ds_assunto_trf"] == "Homicídio Qualificado"
    assert row["cd_classe_judicial"] == "417"
    assert row["nivel_sigilo_processo"] == 0
    assert row["grau_jurisdicao"] == 2
    assert row["ds_md5_documento"] == "abc123"
    assert row["id_orgao_julgador"] == 22
    assert row["id_orgao_julgador_colegiado"] == 12


def test_to_row_defaults_new_fields_when_missing() -> None:
    row = _to_row({"data_julgamento": "2024-01-01"})
    assert row["id_processo"] is None
    assert row["cd_assunto_trf"] == ""
    assert row["nivel_sigilo_processo"] is None
    assert row["id_orgao_julgador"] is None


def test_rows_to_parquet_round_trips_new_int_and_string_fields(tmp_path: Path) -> None:
    """New int64 fields (nivel_sigilo_processo etc.) must not get str()-coerced,
    and a None int field must round-trip as a real parquet null, not "None".
    """
    row = _to_row(_FULL_CRAWLER_DOC)
    missing_row = _to_row({"data_julgamento": "2024-01-01"})
    out = tmp_path / "test.parquet"
    _rows_to_parquet([row, missing_row], out)

    table = pq.read_table(out)
    data = table.to_pylist()
    assert data[0]["id_processo"] == 999
    assert data[0]["nivel_sigilo_processo"] == 0
    assert data[0]["id_orgao_julgador_colegiado"] == 12
    assert data[0]["ds_assunto_trf"] == "Homicídio Qualificado"
    assert data[1]["id_processo"] is None
    assert data[1]["nivel_sigilo_processo"] is None
    assert data[1]["cd_assunto_trf"] == ""

    schema_types = {f.name: f.type for f in table.schema}
    assert str(schema_types["id_processo"]) == "int64"
    assert str(schema_types["nivel_sigilo_processo"]) == "int64"
    assert str(schema_types["ds_assunto_trf"]) == "string"
