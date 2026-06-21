"""Tests for exporter.py — ORDER BY layout and table coverage."""

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
