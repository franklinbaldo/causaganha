"""The per-process ZIP contains a PB pointer, not a copy of the publication."""

import zipfile
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
