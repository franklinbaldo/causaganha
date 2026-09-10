"""Regression coverage for query_plan_fixtures.py's STJ date columns.

service.py's `_stj_sql`/`_documentos_sql` and web/src/lib/processoCnj.ts's
`buildStjSql` both cast STJ's `dataDecisao`/`dataPublicacao` with `::DATE`.
If the underlying fixture column is itself `DATE`-typed, `::DATE` and a
buggy `::VARCHAR` cast produce the identical ISO string ('YYYY-MM-DD'), so
no test can tell them apart -- a real `::DATE` -> `::VARCHAR` regression
would go undetected. The fixture must be `TIMESTAMP`-typed (like the
analogous `datajud.ultima_atualizacao` column) so the two casts genuinely
diverge and this class of regression is actually caught.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

from causaganha.processos.query_plan_fixtures import build_fixtures


if TYPE_CHECKING:
    from pathlib import Path


def test_stj_date_columns_are_timestamp_typed(tmp_path: Path) -> None:
    fixtures = build_fixtures(tmp_path)
    con = duckdb.connect()
    try:
        types = con.execute(
            f"""
            SELECT column_type
            FROM (DESCRIBE SELECT "dataDecisao", "dataPublicacao"
                  FROM read_parquet('{fixtures["stj"]}'))
            """
        ).fetchall()
    finally:
        con.close()

    assert types == [("TIMESTAMP",), ("TIMESTAMP",)], (
        "STJ dataDecisao/dataPublicacao must be TIMESTAMP-typed, not DATE -- "
        "a DATE column casts identically to ::DATE and ::VARCHAR, so it cannot "
        "distinguish a correct ::DATE cast from a buggy ::VARCHAR one "
        f"(got {types})"
    )


def test_stj_date_cast_is_distinguishable_from_varchar_cast(tmp_path: Path) -> None:
    """A ::DATE -> ::VARCHAR regression on STJ dates must change the result.

    This mirrors the exact cast service.py's _stj_sql and processoCnj.ts's
    buildStjSql use (`MAX("dataDecisao")::DATE AS data_decisao`). If the
    fixture column were DATE-typed, both casts below would return the same
    string and this test would fail to prove anything -- the assertion is
    that they must differ, i.e. the fixture must be rich enough (TIMESTAMP,
    non-midnight) to make a ::VARCHAR regression actually visible.
    """
    fixtures = build_fixtures(tmp_path)
    con = duckdb.connect()
    try:
        row = con.execute(
            f"""
            SELECT
                MAX("dataDecisao")::DATE AS correct_cast,
                MAX("dataDecisao")::VARCHAR AS buggy_cast
            FROM read_parquet('{fixtures["stj"]}')
            WHERE id = 'stj-1'
            """
        ).fetchone()
    finally:
        con.close()

    assert row is not None
    correct_cast, buggy_cast = row
    assert str(correct_cast) != buggy_cast, (
        "::DATE and ::VARCHAR casts of STJ dataDecisao produced the same string "
        f"({correct_cast!r}); the fixture must carry a non-midnight TIMESTAMP so "
        "a ::DATE -> ::VARCHAR regression is actually detectable"
    )
    assert str(correct_cast) == "2024-05-01"
