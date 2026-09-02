from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from tcu_acordaos.ingest import REQUIRED_COLUMNS
from tcu_acordaos.materialize import materialize_parquet


def _write_csv(path: Path) -> None:
    fields = [*sorted(REQUIRED_COLUMNS), "VISAOGERAL"]
    row = {field: "" for field in fields}
    row.update(
        {
            "KEY": "TCU-2026-1",
            "NUMACORDAO": "1",
            "ANOACORDAO": "2026",
            "COLEGIADO": "Plenário",
            "DATASESSAO": "2026-01-10",
            "RELATOR": "Ministro Exemplo",
            "PROC": "000.001/2026-0",
            "ASSUNTO": "licitação",
            "ACORDAO": "texto autoritativo",
            "VISAOGERAL": "resumo produzido por IA que não pode virar TEOR",
        }
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="|", quotechar='"')
        writer.writeheader()
        writer.writerow(row)


def test_materialize_preserves_identity_provenance_and_excludes_visao_geral(tmp_path: Path) -> None:
    source = tmp_path / "tcu-2026.csv"
    output = tmp_path / "tcu-2026.parquet"
    _write_csv(source)

    count = materialize_parquet(
        source,
        output,
        source_url="https://sites.tcu.gov.br/dados-abertos/acordao-completo-2026.csv",
        acquired_at="2026-09-02T18:00:00+00:00",
    )

    assert count == 1
    con = duckdb.connect()
    try:
        columns = [row[0] for row in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(output)]).fetchall()]
        record = con.execute(
            "SELECT key, ano, acordao, source_url, source_sha256 FROM read_parquet(?)",
            [str(output)],
        ).fetchone()
    finally:
        con.close()

    assert "VISAOGERAL" not in columns
    assert record is not None
    assert record[:4] == (
        "TCU-2026-1",
        "2026",
        "texto autoritativo",
        "https://sites.tcu.gov.br/dados-abertos/acordao-completo-2026.csv",
    )
    assert len(record[4]) == 64


def test_materialize_rejects_non_parquet_destination(tmp_path: Path) -> None:
    source = tmp_path / "tcu-2026.csv"
    _write_csv(source)

    with pytest.raises(ValueError, match="must end in .parquet"):
        materialize_parquet(
            source,
            tmp_path / "tcu-2026.csv.out",
            source_url="https://sites.tcu.gov.br/dados-abertos/acordao-completo-2026.csv",
            acquired_at="2026-09-02T18:00:00+00:00",
        )
