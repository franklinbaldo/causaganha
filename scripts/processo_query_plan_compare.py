#!/usr/bin/env python3
"""Execute matching Python-service and Web SQL plans against shared fixtures (#1107).

The bridge dispatches to the already-existing private SQL builders in
`causaganha.processos.service` and runs the caller-supplied Web SQL text
(produced by `web/src/lib/processoCnj.ts`'s own builders) through the same
DuckDB engine and the same fixture files. For source plans it also executes
Python's real `_build_*` mapping path and serializes that domain object into
the public Web-view shape, so the parity test covers both raw rows and the
row-to-domain normalization boundary.

Reads a JSON `{"cases": [...]}` file (see `_python_sql` for the per-plan
shape of each case) and writes a JSON list of
`{label, python_sql, python_rows, web_rows, python_mapped}` results.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402 — sys.path bootstrap above

from causaganha.processos import service  # noqa: E402


_SOURCE_PLAN_BUILDERS = {
    "djen": service._djen_sql,
    "juris": service._juris_sql,
    "stj": service._stj_sql,
    "datajud": service._datajud_sql,
}


def _python_sql(case: dict[str, Any]) -> str:
    """Builds the Python-side SQL for one case, dispatching by `case["plan"]`."""
    plan = case["plan"]
    if plan == "documentos":
        sql, _n_params = service._documentos_sql(case["jurisUrls"], case["stjUrls"])
        return sql
    if plan == "indice":
        return service._indice_sql(case["indiceUrl"])
    return _SOURCE_PLAN_BUILDERS[plan](case["urls"])


def _rows(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = con.execute(sql, params)
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _python_mapped(
    con: duckdb.DuckDBPyConnection, case: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    """Run the Python runtime's real source mapper and expose the Web-view shape.

    This intentionally calls `_build_*` rather than reimplementing row mapping
    in the harness. The only translation here is naming: Python domain fields
    are projected to the camelCase public view consumed by the Web parity test.
    `None` for non-source plans keeps the bridge generic for índice/documentos.

    Also returns the `avisos` list `_build_*` collected — e.g. a fonte-specific
    "indisponível" warning when the underlying parquet failed to read (#1107's
    "fonte registrada mas parquet indisponível" ≠ "CNJ ausente" proof needs
    this, not just the mapped present/absent flag, since both states resolve
    to `present: False`).
    """
    plan = case["plan"]
    if plan not in _SOURCE_PLAN_BUILDERS:
        return None, []

    cnj = case["python_params"][0]
    urls = case["urls"]
    avisos: list[str] = []

    if plan == "djen":
        value = service._build_djen(con, urls, cnj, avisos)
        if value is None:
            return {
                "present": False,
                "primeiraPub": None,
                "ultimaPub": None,
                "nPublicacoes": None,
                "tribunais": [],
            }, avisos
        return {
            "present": True,
            "primeiraPub": value.primeira_publicacao,
            "ultimaPub": value.ultima_publicacao,
            "nPublicacoes": value.n_publicacoes,
            "tribunais": value.tribunais,
        }, avisos

    if plan == "juris":
        value = service._build_juris(con, urls, cnj, avisos)
        if value is None:
            return {
                "present": False,
                "nDocumentos": None,
                "tipos": [],
                "dataJulgamento": None,
                "orgao": None,
                "relator": None,
                "classe": None,
                "url": None,
            }, avisos
        return {
            "present": True,
            "nDocumentos": value.n_documentos,
            "tipos": value.tipos,
            "dataJulgamento": value.data_julgamento,
            "orgao": value.orgao,
            "relator": value.relator,
            "classe": value.classe,
            "url": value.url,
        }, avisos

    if plan == "stj":
        value = service._build_stj(con, urls, cnj, avisos)
        if value is None:
            return {
                "present": False,
                "id": None,
                "classe": None,
                "relator": None,
                "tema": None,
                "tese": None,
                "ementa": None,
                "dataDecisao": None,
                "dataPublicacao": None,
            }, avisos
        return {
            "present": True,
            "id": value.id,
            "classe": value.classe,
            "relator": value.relator,
            "tema": value.tema,
            "tese": value.tese,
            "ementa": value.ementa,
            "dataDecisao": value.data_decisao,
            "dataPublicacao": value.data_publicacao,
        }, avisos

    value = service._build_datajud(con, urls, cnj, avisos)
    if value is None:
        return {
            "present": False,
            "classeOficial": None,
            "assuntos": None,
            "orgaoJulgador": None,
            "grau": None,
            "dataAjuizamento": None,
            "ultimaAtualizacao": None,
        }, avisos
    return {
        "present": True,
        "classeOficial": value.classe_oficial,
        "assuntos": value.assuntos,
        "orgaoJulgador": value.orgao_julgador,
        "grau": value.grau,
        "dataAjuizamento": value.data_ajuizamento,
        "ultimaAtualizacao": value.ultima_atualizacao,
    }, avisos


def _safe_rows(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> dict[str, Any]:
    """Like `_rows`, but a genuinely broken parquet (#1107's "fonte indisponível"
    fixture) must not crash the whole comparison run — it is itself the signal
    under test, distinct from a merely-absent CNJ, which never raises.
    """
    try:
        return {"rows": _rows(con, sql, params), "raised": False, "error": None}
    except duckdb.Error as exc:
        return {"rows": [], "raised": True, "error": str(exc)}


def run_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    with duckdb.connect() as con:
        for case in cases:
            python_sql = _python_sql(case)
            python_result = _safe_rows(con, python_sql, case["python_params"])
            web_result = _safe_rows(con, case["web_sql"], case["web_params"])
            mapped, mapped_avisos = _python_mapped(con, case)
            results.append(
                {
                    "label": case["label"],
                    "python_sql": python_sql,
                    "python_rows": python_result["rows"],
                    "python_raised": python_result["raised"],
                    "python_error": python_result["error"],
                    "web_rows": web_result["rows"],
                    "web_raised": web_result["raised"],
                    "web_error": web_result["error"],
                    "python_mapped": mapped,
                    "python_mapped_avisos": mapped_avisos,
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases_file", type=Path)
    parser.add_argument("results_file", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.cases_file.read_text(encoding="utf-8"))
    results = run_cases(payload["cases"])
    # default=str: DuckDB returns native date/Decimal objects for ::DATE/::VARCHAR
    # casts; str() renders a date as its ISO form (e.g. "2024-03-01"), matching
    # both sides' own ISO-normalization (service._iso / processoCnj.ts's toIsoDate).
    args.results_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
