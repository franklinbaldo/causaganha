"""Human-facing CausaGanha CLI."""

from __future__ import annotations

import json
from typing import Annotated

import duckdb
import httpx
from cyclopts import App, Parameter
from rich.console import Console
from rich.table import Table

CATALOG_URL = "https://archive.org/download/causaganha-catalog/catalog.sql"
console = Console()
app = App(name="causaganha", help="Consulte o acervo público do CausaGanha.")


def _connection() -> duckdb.DuckDBPyConnection:
    response = httpx.get(CATALOG_URL, follow_redirects=True, timeout=120.0)
    response.raise_for_status()
    connection = duckdb.connect(":memory:")
    connection.execute(response.text)
    return connection


def _print_query(sql: str, *, output: str = "table") -> None:
    with _connection() as connection:
        cursor = connection.execute(sql)
        columns = [item[0] for item in cursor.description or []]
        rows = cursor.fetchall()

    if output == "json":
        console.print_json(json.dumps([dict(zip(columns, row, strict=True)) for row in rows], default=str))
        return

    table = Table(show_header=True, header_style="bold")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(value) if value is not None else "" for value in row))
    console.print(table)


@app.command
def query(
    sql: Annotated[str, Parameter(help="SQL DuckDB para executar sobre o catálogo público.")],
    *,
    output: Annotated[str, Parameter(help="Formato: table ou json.")] = "table",
) -> None:
    """Execute SQL diretamente sobre o catálogo público."""
    if output not in {"table", "json"}:
        raise ValueError("output deve ser 'table' ou 'json'")
    _print_query(sql, output=output)


@app.command
def comunicacoes(
    *,
    limit: Annotated[int, Parameter(help="Número máximo de resultados.")] = 100,
    tribunal: Annotated[str | None, Parameter(help="Filtrar por tribunal, ex.: TJRO.")] = None,
    output: Annotated[str, Parameter(help="Formato: table ou json.")] = "table",
) -> None:
    """Liste comunicações judiciais do catálogo público."""
    if limit < 1 or limit > 10_000:
        raise ValueError("limit deve estar entre 1 e 10000")
    where = ""
    if tribunal:
        escaped = tribunal.replace("'", "''")
        where = f" WHERE tribunal = '{escaped}'"
    _print_query(f"SELECT * FROM comunicacoes{where} LIMIT {limit}", output=output)


if __name__ == "__main__":
    app()
