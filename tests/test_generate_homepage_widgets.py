from datetime import UTC, datetime
from pathlib import Path

import pytest

import scripts.generate_homepage_widgets as ghw
from scripts.generate_homepage_widgets import _connect, _discover_parquet_urls, build_widgets


def _write_manifest_and_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Write a local catalog: one djen-tjro-2026 item with December 2026 data.

    Mirrors the real causaganha-catalog/manifest.parquet schema (date=NULL for
    the current djen-{tribunal}-{year} consolidated layout) plus the
    comunicacoes/advogados parquets it points to, all under `tmp_path` so the
    test never touches the network.
    """
    com_path = tmp_path / "comunicacoes.parquet"
    adv_path = tmp_path / "advogados.parquet"
    manifest_path = tmp_path / "manifest.parquet"

    con = _connect()
    con.execute("""
        CREATE TABLE comunicacoes (
            intimation_id VARCHAR, sigla_tribunal VARCHAR, numero_processo VARCHAR,
            year INTEGER, month INTEGER, data_disponibilizacao DATE
        )
    """)
    con.execute(
        "INSERT INTO comunicacoes VALUES "
        "('i1', 'TJRO', '0000001-00.2026.8.22.0000', 2026, 12, '2026-12-15')"
    )
    con.execute(f"COPY comunicacoes TO '{com_path}' (FORMAT PARQUET)")

    con.execute("""
        CREATE TABLE advogados (
            intimation_id VARCHAR, oab_number VARCHAR, oab_state VARCHAR
        )
    """)
    con.execute("INSERT INTO advogados VALUES ('i1', '12345', 'RO')")
    con.execute(f"COPY advogados TO '{adv_path}' (FORMAT PARQUET)")

    con.execute("""
        CREATE TABLE manifest (
            date VARCHAR, tribunal VARCHAR, file_type VARCHAR, table_name VARCHAR,
            file_name VARCHAR, ia_item VARCHAR, ia_url VARCHAR, created_at VARCHAR,
            duration_s DOUBLE
        )
    """)
    con.execute(
        "INSERT INTO manifest VALUES "
        "(NULL, 'TJRO', 'parquet', 'comunicacoes', 'comunicacoes.parquet', "
        f"'djen-tjro-2026', '{com_path.as_uri()}', '2026-12-31T00:00:00Z', 1.0), "
        "(NULL, 'TJRO', 'parquet', 'advogados', 'advogados.parquet', "
        f"'djen-tjro-2026', '{adv_path.as_uri()}', '2026-12-31T00:00:00Z', 1.0)"
    )
    con.execute(f"COPY manifest TO '{manifest_path}' (FORMAT PARQUET)")
    con.close()

    monkeypatch.setattr(ghw, "MANIFEST_URL", manifest_path.as_uri())
    # _array_literal only allows https://archive.org/ URLs through (an anti-SQL-
    # injection guard against poisoned manifest rows, unit-tested on its own);
    # relax it here so this test's local file:// fixtures survive that filter
    # too, without weakening the guard itself.
    monkeypatch.setattr(
        ghw,
        "_array_literal",
        lambda urls: "[" + ", ".join(f"'{u}'" for u in urls if isinstance(u, str)) + "]",
    )


def test_build_widgets_finds_last_closed_month_data_across_year_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """activity_summary must find December's data even from a prior-year catalog item.

    build_widgets(year=2027) in January 2027 needs November/December 2026 data
    for its "last closed month" widget, but the only catalog item is
    djen-tjro-2026 -- discovering comunicacoes/advogados URLs solely for the
    requested `year` (2027) finds nothing, so activity_summary silently returns
    {} even though the real December data is sitting right there in the
    previous year's catalog item. This reproduces every January until the
    lookback widens across the year boundary.
    """
    _write_manifest_and_catalog(tmp_path, monkeypatch)

    payload = build_widgets(2027, now=datetime(2027, 1, 15, tzinfo=UTC))

    assert payload["activity_summary"] == {
        "periodo": "2026-12",
        "intimacoes": 1,
        "oabs_unicas": 1,
        "processos": 1,
        "tribunais": 1,
    }


def test_discover_parquet_urls_finds_current_consolidated_layout_rows() -> None:
    """Modern manifest rows for the djen-{tribunal}-{year} layout have date=NULL.

    generate_catalog.py's parse_filename() sets "date": None for the current
    consolidated-parquet layout (a bare comunicacoes.parquet/advogados.parquet
    living inside a djen-{tribunal}-{year} IA item; the year is encoded in the
    item id, not per file). _discover_parquet_urls's year filter must still find
    these rows when a year is requested, since this is the only layout that
    exists in production today -- a filter that only matches a non-NULL `date`
    column silently discards every current-schema row, leaving the homepage
    widgets permanently empty even though real data is present in the catalog.
    """
    con = _connect()
    con.execute("""
        CREATE TABLE manifest (
            date VARCHAR,
            tribunal VARCHAR,
            file_type VARCHAR,
            table_name VARCHAR,
            file_name VARCHAR,
            ia_item VARCHAR,
            ia_url VARCHAR,
            created_at VARCHAR,
            duration_s DOUBLE
        )
    """)
    con.execute(
        """
        INSERT INTO manifest VALUES
        (NULL, 'TJRO', 'parquet', 'comunicacoes', 'comunicacoes.parquet',
         'djen-tjro-2025', 'https://archive.org/download/djen-tjro-2025/comunicacoes.parquet',
         '2025-01-01T00:00:00Z', 1.0)
        """
    )

    urls = _discover_parquet_urls(con, "comunicacoes", year=2025)

    assert urls == ["https://archive.org/download/djen-tjro-2025/comunicacoes.parquet"]


def test_discover_parquet_urls_still_filters_by_year_for_current_layout() -> None:
    """A year that doesn't match any djen-{tribunal}-{year} item must return nothing.

    Guards against a fix that widens the filter so much it stops filtering by
    year at all for the current layout.
    """
    con = _connect()
    con.execute("""
        CREATE TABLE manifest (
            date VARCHAR,
            tribunal VARCHAR,
            file_type VARCHAR,
            table_name VARCHAR,
            file_name VARCHAR,
            ia_item VARCHAR,
            ia_url VARCHAR,
            created_at VARCHAR,
            duration_s DOUBLE
        )
    """)
    con.execute(
        """
        INSERT INTO manifest VALUES
        (NULL, 'TJRO', 'parquet', 'comunicacoes', 'comunicacoes.parquet',
         'djen-tjro-2024', 'https://archive.org/download/djen-tjro-2024/comunicacoes.parquet',
         '2024-01-01T00:00:00Z', 1.0)
        """
    )

    urls = _discover_parquet_urls(con, "comunicacoes", year=2025)

    assert urls == []


def test_discover_parquet_urls_still_matches_legacy_date_column_rows() -> None:
    """Legacy per-day items (djen-YYYY-MM-DD) carry a real `date` value, not NULL.

    The year filter's existing date-column match must keep working for that
    older layout alongside the new ia_item-based match.
    """
    con = _connect()
    con.execute("""
        CREATE TABLE manifest (
            date VARCHAR,
            tribunal VARCHAR,
            file_type VARCHAR,
            table_name VARCHAR,
            file_name VARCHAR,
            ia_item VARCHAR,
            ia_url VARCHAR,
            created_at VARCHAR,
            duration_s DOUBLE
        )
    """)
    con.execute(
        """
        INSERT INTO manifest VALUES
        ('2025-01-15', 'ALL', 'parquet', 'comunicacoes', 'comunicacoes.parquet',
         'djen-2025-01-15', 'https://archive.org/download/djen-2025-01-15/comunicacoes.parquet',
         '2025-01-15T00:00:00Z', 1.0)
        """
    )

    urls = _discover_parquet_urls(con, "comunicacoes", year=2025)

    assert urls == ["https://archive.org/download/djen-2025-01-15/comunicacoes.parquet"]
