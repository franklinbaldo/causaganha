"""The per-process ZIP contains a PB pointer, not a copy of the publication."""

import zipfile

import httpx
import pytest
from pathlib import Path

from scripts.index_djen_originals import (
    apply_source,
    expand_cnj_filename,
    index_item,
    load_partition,
    merge_datajud,
    partition_for,
    remote_partition_name,
    short_cnj_filename,
    write_partition,
)

CNJ = "70726450920238220001"
PUB = (
    "2026-11-09",
    "TJRO-D-2026-11-09_1.json",
    "778704990",
    "JKOdGxm7gYmLtXh1T7mM5lZy5DBkl2",
)


def snapshot(grau, updated="2026-11-09T09:00:00Z"):
    return {
        "tribunal": "TJRO",
        "grau": grau,
        "documento_id": f"TJRO_{grau}_{CNJ}",
        "item_ia": "datajud-tjro",
        "arquivo_zip": "tjro_2026-11-09.zip",
        "membro": f"{CNJ}.json.gz",
        "atualizado_em": updated,
    }


def test_routing_from_cnj_is_filing_year_and_origin():
    assert partition_for(CNJ) == "2023_0001.zip"
    assert index_item("tjro", "2023") == "causaganha-2023-8-22"
    assert remote_partition_name("2023_0001.zip") == "0001.zip"
    assert short_cnj_filename(CNJ) == "707264509.csv"
    assert expand_cnj_filename("707264509.csv", Path("2023_0001.zip")) == CNJ


def test_pointer_zip_roundtrip(tmp_path):
    path = tmp_path / "2023_0001.zip"
    data = {CNJ: {"publicacoes": [PUB, PUB], "datajud": [snapshot("G1"), snapshot("G2")]}}
    write_partition(path, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ["707264509.pb"]
    loaded = load_partition(path)[CNJ]
    assert loaded["publicacoes"] == [PUB]
    assert {row["grau"] for row in loaded["datajud"]} == {"G1", "G2"}


def test_djen_updates_do_not_erase_datajud():
    data = {CNJ: {"publicacoes": [PUB], "datajud": [snapshot("G1")]}}
    later = ("2026-11-10", "new.json", "778704991", "hash-2")
    assert apply_source(data, publication_date="2026-11-10", new_rows={CNJ: [later]})
    assert data[CNJ]["datajud"] == [snapshot("G1")]
    assert not apply_source(data, publication_date="2026-11-10", new_rows={CNJ: [later]})


def test_datajud_upserts_by_document_identity():
    data = {CNJ: {"publicacoes": [PUB], "datajud": [snapshot("G1")]}}
    assert merge_datajud(data, {CNJ: [snapshot("G1", "2026-11-10T00:00:00Z"), snapshot("G2")]})
    assert len(data[CNJ]["datajud"]) == 2
    assert not merge_datajud(data, {CNJ: [snapshot("G1", "2026-11-09T00:00:00Z")]})


def test_empty_djen_leaves_datajud_only_record():
    data = {CNJ: {"publicacoes": [PUB], "datajud": [snapshot("G1")]}}
    assert apply_source(data, publication_date="2026-11-09", new_rows={})
    assert CNJ in data and not data[CNJ]["publicacoes"]


def test_datajud_sidecar_names_are_discovered():
    """Regression: the pattern had doubled escapes and matched nothing."""
    from scripts.index_djen_originals import datajud_sidecar_re

    pattern = datajud_sidecar_re("tjro")
    assert pattern.fullmatch("tjro_2026-11-15.locators.jsonl")
    assert pattern.fullmatch("tjro_2026-11-15T062700Z.locators.jsonl")
    assert not pattern.fullmatch("tjro_2026-11-15T062700Z.zip")
    assert not pattern.fullmatch("tjce_2026-11-15.locators.jsonl")


def _client(routes: dict[str, httpx.Response]):
    def handler(request: httpx.Request) -> httpx.Response:
        return routes[str(request.url)]

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_download_treats_missing_item_503_as_absent(tmp_path):
    """IA serves 503 for downloads from an item that doesn't exist yet."""
    from scripts.index_djen_originals import download

    url = "https://archive.org/download/causaganha-index-control-tjro/manifest.json"
    client = _client(
        {
            url: httpx.Response(503),
            "https://archive.org/metadata/causaganha-index-control-tjro": httpx.Response(
                200, json={}
            ),
        }
    )
    assert download(client, url, tmp_path / "m.json") is False


def test_download_503_on_existing_item_fails_closed(tmp_path):

    from scripts.index_djen_originals import download

    url = "https://archive.org/download/causaganha-index-control-tjro/manifest.json"
    client = _client(
        {
            url: httpx.Response(503),
            "https://archive.org/metadata/causaganha-index-control-tjro": httpx.Response(
                200, json={"metadata": {"identifier": "causaganha-index-control-tjro"}}
            ),
        }
    )
    with pytest.raises(httpx.HTTPStatusError):
        download(client, url, tmp_path / "m.json")


def _publish_fixture(tmp_path, monkeypatch, fail: set[str] | None = None):
    import asyncio

    from causaganha.pipeline import ia_s3

    calls: list[tuple[str, str]] = []

    async def fake_upload(_client, item, path, _date, metadata_overrides=None):
        calls.append((item, path.name))
        return f"{item}/{path.name}" not in (fail or set())

    monkeypatch.setattr(ia_s3, "upload_to_ia", fake_upload)
    monkeypatch.setattr(ia_s3, "get_ia_s3_auth", lambda: "LOW k:s")
    for name in ("2011_0021.zip", "2011_0001.zip", "2026_0022.zip"):
        (tmp_path / name).write_bytes(b"pk")
    (tmp_path / "tjro_manifest.json").write_text("{}")
    report = {
        "tribunal": "tjro",
        "publish_files": ["2011_0021.zip", "2011_0001.zip", "2026_0022.zip", "manifest.json"],
    }
    from scripts.index_djen_originals import publish_report

    return calls, lambda: asyncio.run(publish_report(report, tmp_path))


def test_publish_report_routes_partitions_and_sends_manifest_last(tmp_path, monkeypatch):
    calls, run = _publish_fixture(tmp_path, monkeypatch)
    assert run() == 4
    assert set(calls[:-1]) == {
        ("causaganha-2011-8-22", "0021.zip"),
        ("causaganha-2011-8-22", "0001.zip"),
        ("causaganha-2026-8-22", "0022.zip"),
    }
    assert calls[-1] == ("causaganha-index-control-tjro", "manifest.json")


def test_publish_report_withholds_manifest_when_a_partition_fails(tmp_path, monkeypatch):
    calls, run = _publish_fixture(tmp_path, monkeypatch, fail={"causaganha-2011-8-22/0021.zip"})
    with pytest.raises(RuntimeError, match="manifest withheld"):
        run()
    assert ("causaganha-index-control-tjro", "manifest.json") not in calls
