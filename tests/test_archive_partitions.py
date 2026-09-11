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


def test_verification_waits_for_metadata_propagation_without_reupload(monkeypatch):
    from scripts.pipeline import consolidate_partition as runner
    from tenacity import stop_after_attempt, wait_none

    before = {"fingerprint": "same", "files": FILES}
    after = {**before, "files": FILES + [{"name": "comunicacoes.parquet", "md5": "output"}]}
    read_inventory = Mock(side_effect=[before, after])
    monkeypatch.setattr(runner, "inventory", read_inventory)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(206, content=b"PAR1"),
        )
    ) as client:
        verify = runner.verify_outputs.retry_with(stop=stop_after_attempt(2), wait=wait_none())
        result = verify(client, ITEM, before, {"comunicacoes.parquet": "output"})
    assert result == [{"name": "comunicacoes.parquet", "md5": "output"}]
    assert read_inventory.call_count == 2


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


def test_changed_zip_bytes_are_rejected_before_extraction(monkeypatch, tmp_path):
    from scripts.pipeline import consolidate as module

    def download(item, name, path):
        path.write_bytes(b"stale ZIP bytes")
        return True

    monkeypatch.setattr(module, "download_zip", download)
    extract = Mock()
    monkeypatch.setattr(module, "extract_json_from_zip", extract)
    with pytest.raises(RuntimeError, match="does not match"):
        module.process_zip_entry(
            {"filename": "test.zip", "tribunal": "TJRO", "md5": "different", "size": 15},
            tmp_path,
            tmp_path,
            "djen-tjro-2026",
            None,
        )
    extract.assert_not_called()


def test_catalog_rejects_a_partially_replaced_output_set():
    from scripts.generate_catalog import certified_parquet_names

    files = [
        {"name": "comunicacoes.parquet", "md5": "new"},
        {"name": "textos.parquet", "md5": "old"},
    ]
    receipt = {
        "outputs": [
            {"name": "comunicacoes.parquet", "md5": "new"},
            {"name": "textos.parquet", "md5": "new"},
        ]
    }
    assert certified_parquet_names(files, receipt) == set()
    files[1]["md5"] = "new"
    assert certified_parquet_names(files, receipt) == {"comunicacoes.parquet", "textos.parquet"}


def test_full_catalog_inventory_failure_propagates(monkeypatch):
    from scripts import generate_catalog as catalog

    async def failed(*args, **kwargs):
        message = "upstream down"
        raise OSError(message)

    monkeypatch.setattr(catalog, "fetch_item_files", failed)
    with pytest.raises(OSError, match="upstream down"):
        catalog.generate_manifest([ITEM], verified_inventory=True)


def test_daily_rotation_does_not_starve_later_partitions(monkeypatch):
    from scripts.pipeline import archive_partitions as module

    items = [f"djen-test{i}-2026" for i in range(5)]
    monkeypatch.setattr(module, "discover", lambda _: items)
    monkeypatch.setattr(module, "inventory", lambda _, item: {"item": item, "year": 2026})
    monkeypatch.setattr(module, "needs_consolidation", lambda *_: True)
    with client_for(FILES) as client:
        selected = {
            part["item"] for day in range(5) for part in module.plan(client, None, 2, day=day)
        }
    assert selected == set(items)


def client_for(files, receipt=None):
    def handle(request):
        if "/metadata/" in request.url.path:
            return httpx.Response(200, json={"result": files})
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
