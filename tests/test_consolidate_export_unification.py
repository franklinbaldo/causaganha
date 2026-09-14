"""_export_table_sync in scripts/pipeline/consolidate.py delegates to the
shared causaganha.consolidate.exporter.export_table_sync — no duplicated,
unordered/un-normalized COPY logic (issue #1469, acceptance criterion 1)."""

from __future__ import annotations

import duckdb
import ibis

from causaganha.consolidate.transforms import init_tables
from scripts.pipeline.consolidate import _export_table_sync


def test_legacy_export_path_applies_cnj_normalization_and_ordering(tmp_path) -> None:
    con = ibis.duckdb.connect(":memory:")
    init_tables(con)
    con.raw_sql("""
        INSERT INTO comunicacoes
        SELECT
            gen_random_uuid()::VARCHAR AS id,
            'orig-1' AS original_id,
            'TJSP' AS tribunal,
            '0001234-56.2026.8.26.0100' AS numero_processo,
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

    result = _export_table_sync("comunicacoes", con, tmp_path, "djen-tjsp-2026")
    assert result is not None

    path = tmp_path / "comunicacoes.parquet"
    (value,) = duckdb.execute(f"SELECT numero_processo FROM '{path}'").fetchone()
    assert value == "00012345620268260100", (
        "legacy _export_table_sync must apply the same CNJ normalization as "
        "causaganha.consolidate.exporter.export_table_sync"
    )

    kv = dict(duckdb.execute(f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall())
    kv = {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in kv.items()
    }
    assert kv["causaganha.layout"] == "cnj-text-sorted-v1", (
        "legacy _export_table_sync must certify the same layout footer as the modular exporter"
    )
