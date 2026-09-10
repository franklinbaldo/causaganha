from scripts.generate_homepage_widgets import _connect, _discover_parquet_urls


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
