from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcu_acordaos.ingest import (
    REQUIRED_COLUMNS,
    AcquisitionProvenance,
    canonical_key,
    load_csv,
    search_teor,
    transform_rows,
)


def _row(**overrides: str) -> dict[str, str]:
    row = {column: "" for column in REQUIRED_COLUMNS}
    row.update(
        {
            "KEY": "AC-123",
            "TIPO": "Acórdão",
            "TITULO": "ACÓRDÃO 123/2026 - PLENÁRIO",
            "NUMACORDAO": "123",
            "ANOACORDAO": "2026",
            "COLEGIADO": "Plenário",
            "DATASESSAO": "01/09/2026",
            "RELATOR": "Ministro Exemplo",
            "SITUACAO": "Oficializado",
            "PROC": "000.000/2026-0",
            "ASSUNTO": "Licitação",
            "SUMARIO": "Representação sobre contratação pública",
            "ACORDAO": "Os Ministros acordam em determinar a correção do edital.",
            "DECISAO": "Determinar a correção do edital.",
            "RELATORIO": "Relatório dos fatos.",
            "VOTO": "Voto pela procedência parcial.",
        }
    )
    row.update(overrides)
    return row


def _provenance() -> AcquisitionProvenance:
    return AcquisitionProvenance(
        source_url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/acordaos-2026.csv",
        acquired_at="2026-09-02T12:00:00Z",
        sha256="a" * 64,
    )


def test_canonical_key_uses_official_key_without_synthesizing() -> None:
    row = _row(KEY=" chave-oficial ", NUMACORDAO="999", ANOACORDAO="2030")

    assert canonical_key(row) == "chave-oficial"


def test_canonical_key_rejects_missing_official_identity() -> None:
    with pytest.raises(ValueError, match="official KEY"):
        canonical_key(_row(KEY="  "))


def test_transform_preserves_primary_source_provenance_and_authoritative_text() -> None:
    provenance = _provenance()

    [record] = transform_rows([_row()], provenance=provenance)

    assert record.key == "AC-123"
    assert record.acordao.startswith("Os Ministros acordam")
    assert record.source_url == provenance.source_url
    assert record.acquired_at == provenance.acquired_at
    assert record.source_sha256 == provenance.sha256
    assert not hasattr(record, "visao_geral")


def test_transform_rejects_duplicate_official_keys() -> None:
    rows = [_row(), _row(NUMACORDAO="124")]

    with pytest.raises(ValueError, match="duplicate official TCU KEY"):
        transform_rows(rows, provenance=_provenance())


def test_search_teor_matches_authoritative_fields_case_insensitively() -> None:
    records = transform_rows(
        [_row(), _row(KEY="AC-456", ACORDAO="Matéria tributária sem relação.")],
        provenance=_provenance(),
    )

    result = search_teor(records, "CORREÇÃO DO EDITAL")

    assert [record.key for record in result] == ["AC-123"]


def test_load_csv_requires_documented_tcu_schema(tmp_path: Path) -> None:
    path = tmp_path / "missing.csv"
    path.write_text("KEY,ACORDAO\nAC-1,texto\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing documented columns"):
        load_csv(path)


def test_load_csv_accepts_utf8_bom_and_documented_schema(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerow(_row())

    [row] = load_csv(path)

    assert row["KEY"] == "AC-123"


def test_provenance_hashes_exact_input_bytes(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    path.write_bytes(b"official-bytes\n")

    provenance = AcquisitionProvenance.from_file(
        path,
        source_url="https://sites.tcu.gov.br/example.csv",
        acquired_at="2026-09-02T12:00:00Z",
    )

    assert provenance.sha256 == "c5683fcd9157568e0bc7d54c24fcd8fac16170a1f005ea5f5f400e227f7174ff"
