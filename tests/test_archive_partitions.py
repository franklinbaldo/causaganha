"""Archive inventory is sufficient to schedule available data without national completeness."""

import copy
from pathlib import Path
from unittest.mock import Mock

import httpx
import duckdb
import pytest
import yaml

from scripts.pipeline.archive_partitions import RECEIPT, inventory, needs_consolidation, plan
from scripts.pipeline.consolidate_partition import sync_entries


ITEM = "djen-tre-ro-2026"
FILES = [{"name": "djen-2026-09-04-TRE-RO.zip", "size": "123", "md5": "abc"}]


def test_index_prefers_annual_copy_without_duplicating_publications():
    from scripts.reconcile_processos import _INDICE_DJEN_SQL

    with duckdb.connect() as con:
        con.execute("""CREATE TABLE comunicacoes AS SELECT * FROM (VALUES
            ('70083321620268220007', 'TJRO', 'same-id', DATE '2026-09-04', 'djen-2026-09-04'),
            ('70083321620268220007', 'TJRO', 'same-id', DATE '2026-09-04', 'djen-tjro-2026'),
            ('70083321620268220007', 'TJRO', 'other-id', DATE '2026-09-04', 'djen-tjro-2026')
        ) t(numero_processo, tribunal, id, data_disponibilizacao, p_item_ia)""")
        rows = con.execute(_INDICE_DJEN_SQL).fetchall()
    assert len(rows) == 2
    assert all(row[-1].endswith("/djen-tjro-2026/comunicacoes.parquet") for row in rows)


def client_for(files, receipt=None):
    def handle(request):
        if "/metadata/" in request.url.path:
            return httpx.Response(200, json={"files": files})
        return httpx.Response(200, json=receipt)

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_available_tribunal_is_scheduled_without_other_courts():
    with client_for(FILES) as client:
        assert plan(client, ITEM, 12) == [{"item": ITEM}]
        snapshot = inventory(client, ITEM)
    assert snapshot["tribunal"] == "TRE-RO"
    assert list(sync_entries(snapshot)) == ["2026-09-04"]


def test_receipt_tracks_inputs_and_published_outputs():
    files = copy.deepcopy(FILES) + [
        {"name": RECEIPT},
        {"name": "comunicacoes.parquet", "md5": "output"},
    ]
    with client_for(files) as client:
        snapshot = inventory(client, ITEM)
    receipt = {
        "fingerprint": snapshot["fingerprint"],
        "outputs": [{"name": "comunicacoes.parquet", "md5": "output"}],
    }
    with client_for(files, receipt) as client:
        assert not needs_consolidation(client, inventory(client, ITEM))
        files[0]["md5"] = "changed"
        assert needs_consolidation(client, inventory(client, ITEM))
        files[0]["md5"] = "abc"
        files.append({"name": "djen-2026-09-05-TRE-RO.zip", "size": 5, "md5": "new"})
        assert needs_consolidation(client, inventory(client, ITEM))
        files.pop()
        files[-1]["md5"] = "corrupt"
        assert needs_consolidation(client, inventory(client, ITEM))


@pytest.mark.parametrize("status,body", [(503, {}), (200, {}), (200, {"files": None})])
def test_failed_inventory_never_becomes_no_work(status, body):
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, json=body),
            )
        ) as client,
        pytest.raises((ValueError, TypeError, httpx.HTTPError)),
    ):
        plan(client, ITEM, 12)


def test_failed_zip_blocks_partition_before_export(monkeypatch):
    from scripts.pipeline import consolidate as module

    monkeypatch.setattr(module, "get_connection", lambda *_: Mock())
    monkeypatch.setattr(module, "init_tables", lambda *_: None)
    monkeypatch.setattr(module, "process_zip_entry", lambda *_: (0, 0))
    export = Mock()
    monkeypatch.setattr(module, "_export_and_upload_table", export)
    with client_for(FILES) as client:
        snapshot = inventory(client, ITEM)
    with pytest.raises(RuntimeError, match="failed ZIPs"):
        module.consolidate_tribunal_year("TRE-RO", 2026, sync_entries(snapshot), dry_run=True)
    export.assert_not_called()


def test_catalog_refresh_is_not_gated_on_new_zips():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/update-catalog.yml").read_text())
    steps = workflow["jobs"]["catalog"]["steps"]
    for name in [
        "Generate reconstructible catalog",
        "Reconcile processos (DJEN x JURIS x STJ x DataJud)",
    ]:
        step = next(step for step in steps if step.get("name") == name)
        assert "force_reconcile" in step["if"]
    generate = next(
        step for step in steps if step.get("name") == "Generate reconstructible catalog"
    )
    assert "--full" in generate["run"]


@pytest.mark.parametrize("dry_run", [True, False])
def test_runner_never_certifies_dry_run_or_changed_inputs(monkeypatch, dry_run):
    from scripts.pipeline import consolidate as converter
    from scripts.pipeline import consolidate_partition as runner

    with client_for(FILES) as client:
        before = inventory(client, ITEM)
    after = {**before, "fingerprint": "changed-during-run"}
    monkeypatch.setattr(runner, "inventory", Mock(side_effect=[before, after]))
    monkeypatch.setattr(runner, "get_ia_s3_auth", lambda: "test-only")
    monkeypatch.setattr(converter, "consolidate_tribunal_year", Mock(return_value={"uploaded": 1}))
    publish = Mock()
    monkeypatch.setattr(runner, "publish_receipt", publish)
    if dry_run:
        runner.run(ITEM, dry_run=True)
    else:
        with pytest.raises(RuntimeError, match="inventory changed"):
            runner.run(ITEM)
    publish.assert_not_called()
