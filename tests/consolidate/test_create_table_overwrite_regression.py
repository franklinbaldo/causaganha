"""Regression test for issue #1061.

``ibis.duckdb.Backend.create_table(..., overwrite=True)`` routes its
drop-before-create step through ``sqlglot.expressions.Drop(kind="TABLE",
exists=True)``. On the pinned ibis/duckdb/sqlglot stack this renders as the
bare string ``"DROP TABLE IF EXISTS"`` — the table name is missing — which
DuckDB rejects with a ``ParserException``. This breaks ``overwrite=True`` on
*every* call, including the very first table creation on a fresh connection,
because ibis always executes the drop step unconditionally when
``overwrite=True``.

``init_tables`` must therefore not rely on ``create_table(overwrite=True)``.
"""

from __future__ import annotations

import ibis

from causaganha.consolidate.transforms import TABLE_SCHEMAS, init_tables


def test_init_tables_does_not_use_broken_create_table_overwrite() -> None:
    """``init_tables`` must succeed on a fresh connection.

    This is the exact failure mode from issue #1061: calling
    ``con.create_table(name, schema=schema, overwrite=True)`` raises
    ``duckdb.ParserException: Parser Error: syntax error at end of input``
    on the pinned stack, even though the table does not exist yet.
    """
    con = ibis.duckdb.connect()

    init_tables(con)

    for table in TABLE_SCHEMAS:
        assert con.table(table).count().execute() == 0


def test_init_tables_is_idempotent_on_an_existing_connection() -> None:
    """Re-running ``init_tables`` (e.g. between test cases sharing a fixture)
    must reset tables to empty rather than raising or leaving stale rows.
    """
    con = ibis.duckdb.connect()

    init_tables(con)
    first_table = next(iter(TABLE_SCHEMAS))
    con.insert(first_table, con.table(first_table).limit(0))

    init_tables(con)

    for table in TABLE_SCHEMAS:
        assert con.table(table).count().execute() == 0
