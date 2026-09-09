"""Dry-run consolidation must still register non-empty-table stats in the manifest.

``--dry-run`` skips IA uploads, but the intent (per the inline comment in
``_export_upload_and_manifest``) is that stats for non-empty tables are still
registered to the consolidation manifest. ``_uploads_complete`` gated the
manifest write on ``stats["uploaded"] == expected``, but ``stats["uploaded"]``
is never incremented in dry-run mode (nothing is actually uploaded) — so the
gate was unreachable whenever there was real, non-empty data to consolidate.
"""

from __future__ import annotations

import asyncio

import ibis
import pytest

from causaganha.consolidate import cli as cli_module
from causaganha.consolidate.transforms import init_tables


def _seed_one_comunicacao(con: ibis.BaseBackend) -> None:
    con.raw_sql("""
        INSERT INTO comunicacoes
        SELECT
            gen_random_uuid()::VARCHAR AS id,
            'orig-1' AS original_id,
            'TJSP' AS tribunal,
            '' AS numero_processo,
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


@pytest.fixture
def _no_ia_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IAS3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IAS3_SECRET_KEY", raising=False)


def test_dry_run_with_real_data_still_registers_manifest_stats(
    tmp_path, monkeypatch: pytest.MonkeyPatch, _no_ia_credentials: None
) -> None:
    manifest_calls: list[dict] = []
    monkeypatch.setattr(
        cli_module,
        "update_consolidation_manifest",
        lambda **kwargs: manifest_calls.append(kwargs),
    )

    con = ibis.duckdb.connect(":memory:")
    init_tables(con)
    _seed_one_comunicacao(con)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    stats: dict[str, int | float] = {
        "zips_processed": 0,
        "records": 1,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
        "export_failures": 0,
        "marker_uploaded": 0,
    }

    asyncio.run(
        cli_module._export_upload_and_manifest(
            con,
            output_dir,
            "djen-tjsp-2026",
            "2026-01-01",
            {"comunicacoes"},
            stats,
            dry_run=True,
            ndjson_dir=None,
        )
    )

    assert stats["marker_uploaded"] == 1, (
        "dry-run with real, cleanly-exported data must still be able to "
        "register manifest stats -- it must not require an IA upload count "
        "that dry-run mode can never produce"
    )
    assert manifest_calls, "update_consolidation_manifest was never called"
    assert manifest_calls[0]["item_id"] == "djen-tjsp-2026"
    assert "comunicacoes" in manifest_calls[0]["table_stats"]
