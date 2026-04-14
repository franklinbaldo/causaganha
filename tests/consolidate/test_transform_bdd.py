"""BDD step definitions for tests/consolidate/features/transform.feature."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import ibis
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from causaganha.consolidate.transforms import init_tables, load_and_transform


scenarios("features/transform.feature")


SAMPLE_WIN = {
    "id": "W1",
    "texto": "JULGO PROCEDENTE o pedido do autor para condenar o réu.",
    "numeroProcesso": "0001234-56.2026.8.26.0100",
    "dataDisponibilizacao": "2026-04-01",
    "tipoComunicacao": "Intimação",
    "nomeOrgao": "1ª Vara Cível",
    "meio": "Eletrônico",
    "link": "https://example.com",
    "tipoDocumento": "Sentença",
    "nomeClasse": "Procedimento Comum",
    "codigoClasse": "7",
    "numeroComunicacao": "001",
    "hash": "abcwin",
    "destinatarios": [
        {"nome": "JOÃO DA SILVA", "polo": "Ativo"},
        {"nome": "EMPRESA XYZ LTDA", "polo": "Passivo"},
    ],
    "destinatarioadvogados": [
        {"advogado": {"nome": "DRA MARIA OLIVEIRA", "numeroOAB": "12345", "ufOAB": "SP"}},
        {"advogado": {"nome": "DR PEDRO SANTOS", "numeroOAB": "67890", "ufOAB": "SP"}},
    ],
}

SAMPLE_LOSS = {
    **SAMPLE_WIN,
    "id": "L1",
    "texto": "JULGO IMPROCEDENTE o pedido formulado pelo autor.",
    "hash": "abcloss",
}


def _write_ndjson(ndjson_dir: Path, tribunal: str, records: list[dict[str, Any]]) -> None:
    ndjson_path = ndjson_dir / f"{tribunal}__synthetic.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec))
            f.write("\n")


@pytest.fixture
def tmpdir() -> Any:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@given("a synthetic NDJSON record with a WIN outcome")
def given_win(tmpdir: Path, context: dict[str, Any]) -> None:
    ndjson_dir = tmpdir / "ndjson"
    ndjson_dir.mkdir()
    _write_ndjson(ndjson_dir, "TJSP", [SAMPLE_WIN])
    context["ndjson_dir"] = ndjson_dir


@given("that record has 2 parties and 2 lawyers")
def _noop_two_each() -> None:
    # Already in SAMPLE_WIN
    pass


@given("a synthetic NDJSON record with an improcedente verdict")
def given_loss(tmpdir: Path, context: dict[str, Any]) -> None:
    ndjson_dir = tmpdir / "ndjson"
    ndjson_dir.mkdir()
    _write_ndjson(ndjson_dir, "TJRS", [SAMPLE_LOSS])
    context["ndjson_dir"] = ndjson_dir


@when(parsers.parse("I run the transform for item_id {item_id}"))
def run_transform(context: dict[str, Any], item_id: str) -> None:
    con = ibis.duckdb.connect(":memory:")
    init_tables(con)
    counts = load_and_transform(con, context["ndjson_dir"], item_id)
    context["con"] = con
    context["counts"] = counts


@then(parsers.parse("{table_name} has {n:d} row"))
def check_rows_singular(context: dict[str, Any], table_name: str, n: int) -> None:
    count = int(context["con"].table(table_name).count().execute())
    assert count == n, f"{table_name}: expected {n}, got {count}"


@then(parsers.parse("{table_name} has {n:d} rows"))
def check_rows_plural(context: dict[str, Any], table_name: str, n: int) -> None:
    count = int(context["con"].table(table_name).count().execute())
    assert count == n, f"{table_name}: expected {n}, got {count}"


@then(parsers.parse("the classificacoes outcome is {outcome}"))
def check_outcome(context: dict[str, Any], outcome: str) -> None:
    result = context["con"].raw_sql("SELECT outcome FROM classificacoes").fetchall()
    assert len(result) == 1, f"Expected 1 classificacao row, got {len(result)}"
    assert result[0][0] == outcome, f"Expected {outcome}, got {result[0][0]}"
