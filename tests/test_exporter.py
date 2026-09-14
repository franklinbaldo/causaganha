"""Tests for exporter.py — ORDER BY layout, CNJ normalization and table coverage."""

from __future__ import annotations

import duckdb

from causaganha.consolidate.exporter import _TABLE_ORDER_KEYS
from causaganha.consolidate.transforms import TABLES


class TestTableOrderKeys:
    def test_every_table_has_an_order_key(self) -> None:
        for table in TABLES:
            assert table in _TABLE_ORDER_KEYS, (
                f"Table '{table}' has no entry in _TABLE_ORDER_KEYS. "
                "Add an ORDER BY key for A1 row-group pruning."
            )

    def test_order_keys_are_valid_column_names(self) -> None:
        from causaganha.consolidate.schema_registry import get_current_schema

        schema = get_current_schema()
        for table, order_keys_str in _TABLE_ORDER_KEYS.items():
            table_schema = schema.tables[table]
            for col in [k.strip() for k in order_keys_str.split(",")]:
                assert col in table_schema, (
                    f"Column '{col}' in _TABLE_ORDER_KEYS['{table}'] "
                    f"does not exist in schema. Available: {list(table_schema)}"
                )

    def test_export_produces_sorted_parquet(self, tmp_path) -> None:
        """Comunicacoes rows are written in data_disponibilizacao order."""
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)

        con.raw_sql("""
            INSERT INTO comunicacoes
            SELECT
                gen_random_uuid()::VARCHAR AS id,
                'orig-' || CAST(i AS VARCHAR) AS original_id,
                'TJSP' AS tribunal,
                '' AS numero_processo,
                '' AS numero_processo_mascara,
                DATE '2026-01-01' + INTERVAL (100 - i) DAY AS data_disponibilizacao,
                '' AS tipo_comunicacao,
                '' AS nome_orgao,
                '' AS meio,
                '' AS link,
                '' AS tipo_documento,
                '' AS nome_classe,
                '' AS codigo_classe,
                '' AS numero_comunicacao,
                '' AS hash,
                NOW() AS processed_at,
                gen_random_uuid()::VARCHAR AS texto_id,
                2026 AS p_ano,
                MONTH(DATE '2026-01-01' + INTERVAL (100 - i) DAY) AS p_mes,
                'djen-tjsp-2026' AS p_item_ia
            FROM range(1, 11) AS t(i)
        """)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        assert path.exists()
        dates = duckdb.execute(f"SELECT data_disponibilizacao FROM '{path}'").fetchall()
        date_vals = [r[0] for r in dates]
        assert date_vals == sorted(date_vals), "comunicacoes not sorted by data_disponibilizacao"

    def test_comunicacoes_ordered_by_cnj_then_date_then_id(self) -> None:
        assert _TABLE_ORDER_KEYS["comunicacoes"] == "numero_processo, data_disponibilizacao, id"

    def test_processos_ordered_by_cnj_then_date(self) -> None:
        assert _TABLE_ORDER_KEYS["processos"] == "numero_processo, data"


def _insert_comunicacao(con, *, numero_processo: str | None, i: int) -> None:
    """Insert one minimal comunicacoes row, numero_processo given as a SQL literal."""
    literal = "NULL" if numero_processo is None else f"'{numero_processo}'"
    con.raw_sql(f"""
        INSERT INTO comunicacoes
        SELECT
            gen_random_uuid()::VARCHAR AS id,
            'orig-' || CAST({i} AS VARCHAR) AS original_id,
            'TJSP' AS tribunal,
            {literal} AS numero_processo,
            '' AS numero_processo_mascara,
            DATE '2026-01-01' AS data_disponibilizacao,
            '' AS tipo_comunicacao,
            '' AS nome_orgao,
            '' AS meio,
            '' AS link,
            '' AS tipo_documento,
            '' AS nome_classe,
            '' AS codigo_classe,
            '' AS numero_comunicacao,
            '' AS hash,
            NOW() AS processed_at,
            gen_random_uuid()::VARCHAR AS texto_id,
            2026 AS p_ano,
            1 AS p_mes,
            'djen-tjsp-2026' AS p_item_ia
    """)


class TestCnjNormalization:
    """`numero_processo` is normalized to 20-digit text only when it round-trips."""

    def test_masked_cnj_is_normalized_to_20_digit_text(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        _insert_comunicacao(con, numero_processo="0001234-56.2026.8.26.0100", i=1)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        (value,) = duckdb.execute(f"SELECT numero_processo FROM '{path}'").fetchone()
        assert value == "00012345620268260100"

    def test_non_cnj_value_is_preserved_unchanged(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        _insert_comunicacao(con, numero_processo="", i=1)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        (value,) = duckdb.execute(f"SELECT numero_processo FROM '{path}'").fetchone()
        assert value == ""

    def test_null_numero_processo_stays_null(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        _insert_comunicacao(con, numero_processo=None, i=1)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        (value,) = duckdb.execute(f"SELECT numero_processo FROM '{path}'").fetchone()
        assert value is None

    def test_other_columns_and_row_count_are_unaffected(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        _insert_comunicacao(con, numero_processo="0001234-56.2026.8.26.0100", i=1)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        row = duckdb.execute(f"SELECT tribunal, original_id FROM '{path}'").fetchone()
        assert row == ("TJSP", "orig-1")


class TestCnjLayoutCertification:
    """Only CNJ-normalized/sorted tables carry the layout footer markers."""

    def test_comunicacoes_footer_declares_cnj_layout(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        _insert_comunicacao(con, numero_processo="0001234-56.2026.8.26.0100", i=1)

        export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "comunicacoes.parquet"
        kv = dict(
            duckdb.execute(f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall()
        )
        kv = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in kv.items()
        }
        assert kv["causaganha.layout"] == "cnj-text-sorted-v1"
        assert kv["causaganha.cnj_normalization"] == "valid-20-digits-v1"

    def test_table_without_cnj_column_has_no_layout_markers(self, tmp_path) -> None:
        import ibis

        from causaganha.consolidate.exporter import export_table_sync
        from causaganha.consolidate.transforms import init_tables

        con = ibis.duckdb.connect(":memory:")
        init_tables(con)
        con.raw_sql("""
            INSERT INTO textos SELECT gen_random_uuid()::VARCHAR AS id, 'texto' AS texto
        """)

        export_table_sync("textos", con, tmp_path, "djen-tjsp-2026")

        path = tmp_path / "textos.parquet"
        kv = dict(
            duckdb.execute(f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall()
        )
        keys = {k.decode() if isinstance(k, bytes) else k for k in kv}
        assert "causaganha.layout" not in keys
        assert "causaganha.cnj_normalization" not in keys
