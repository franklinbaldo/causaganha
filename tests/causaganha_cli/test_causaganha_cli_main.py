"""Behavior tests for the human-facing ``causaganha`` CLI (PyPI package, #1258).

Shipped to PyPI (1.0.3) with zero test coverage. `_connection()` is the only
network/IO boundary (a DuckDB in-memory connection loaded from the public
`catalog.sql` fetched over HTTP); every other function is pure DuckDB/Rich
logic. Tests below monkeypatch `_connection` to a fixture-backed in-memory
DuckDB connection so `query`/`comunicacoes` are exercised end-to-end
(argv -> SQL -> rendered output) without touching the network, plus a
dedicated pair of tests for `_connection` itself against a monkeypatched
`httpx.get`.
"""

from __future__ import annotations

import json

import duckdb
import httpx
import pytest

from causaganha_cli import __main__ as cli


@pytest.fixture
def fake_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point `_connection` at an in-memory DB seeded with a `comunicacoes` table."""

    def _fake_connection() -> duckdb.DuckDBPyConnection:
        connection = duckdb.connect(":memory:")
        connection.execute(
            "CREATE TABLE comunicacoes (id INTEGER, tribunal VARCHAR, texto VARCHAR)"
        )
        connection.execute(
            "INSERT INTO comunicacoes VALUES "
            "(1, 'TJRO', 'primeira'), (2, 'TJSP', 'segunda'), (3, 'TJRO', 'terceira')"
        )
        return connection

    monkeypatch.setattr(cli, "_connection", _fake_connection)


# ── _connection ─────────────────────────────────────────────────────────


def test_connection_executes_the_downloaded_catalog_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeResponse:
        text = "CREATE TABLE t AS SELECT 42 AS answer;"

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url: str, *, follow_redirects: bool, timeout: float) -> _FakeResponse:
        assert url == cli.CATALOG_URL
        assert follow_redirects is True
        return _FakeResponse()

    monkeypatch.setattr(cli.httpx, "get", _fake_get)

    with cli._connection() as connection:
        assert connection.execute("SELECT answer FROM t").fetchone() == (42,)


def test_connection_propagates_http_errors_without_swallowing_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingResponse:
        text = ""

        def raise_for_status(self) -> None:
            request = httpx.Request("GET", cli.CATALOG_URL)
            response = httpx.Response(503, request=request)
            msg = "service unavailable"
            raise httpx.HTTPStatusError(msg, request=request, response=response)

    monkeypatch.setattr(cli.httpx, "get", lambda *a, **k: _FailingResponse())

    with pytest.raises(httpx.HTTPStatusError):
        cli._connection()


# ── query ───────────────────────────────────────────────────────────────


def test_query_command_runs_arbitrary_sql_and_prints_a_table(
    fake_catalog: None, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.query("SELECT id, tribunal FROM comunicacoes WHERE id = 1")

    out = capsys.readouterr().out
    assert "tribunal" in out
    assert "TJRO" in out
    assert "TJSP" not in out


def test_query_command_json_output_is_valid_json(
    fake_catalog: None, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.query("SELECT id, tribunal FROM comunicacoes ORDER BY id", output="json")

    payload = json.loads(capsys.readouterr().out)
    assert payload == [
        {"id": 1, "tribunal": "TJRO"},
        {"id": 2, "tribunal": "TJSP"},
        {"id": 3, "tribunal": "TJRO"},
    ]


def test_query_command_rejects_invalid_output_format(fake_catalog: None) -> None:
    with pytest.raises(ValueError, match="output deve ser 'table' ou 'json'"):
        cli.query("SELECT 1", output="xml")


# ── comunicacoes ────────────────────────────────────────────────────────


def test_comunicacoes_defaults_list_every_row_up_to_the_limit(
    fake_catalog: None, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.comunicacoes()

    out = capsys.readouterr().out
    assert "TJRO" in out
    assert "TJSP" in out


def test_comunicacoes_filters_by_tribunal(
    fake_catalog: None, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.comunicacoes(tribunal="TJRO", output="json")

    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 2
    assert all(row["tribunal"] == "TJRO" for row in payload)


def test_comunicacoes_escapes_single_quotes_in_tribunal_filter(
    fake_catalog: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """A tribunal value containing `'` must not break out of the SQL string literal."""
    cli.comunicacoes(tribunal="TJ'RO", output="json")

    payload = json.loads(capsys.readouterr().out)
    assert payload == []  # no match, but no SQL syntax error either


@pytest.mark.parametrize("limit", [0, -1, 10_001])
def test_comunicacoes_rejects_out_of_range_limit(fake_catalog: None, limit: int) -> None:
    with pytest.raises(ValueError, match="limit deve estar entre 1 e 10000"):
        cli.comunicacoes(limit=limit)


def test_comunicacoes_rejects_invalid_output_format(fake_catalog: None) -> None:
    """`comunicacoes` must validate `output` the same way `query` already does."""
    with pytest.raises(ValueError, match="output deve ser 'table' ou 'json'"):
        cli.comunicacoes(output="xml")
