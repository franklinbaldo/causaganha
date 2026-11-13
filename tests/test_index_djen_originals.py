"""Tests for sharded DJEN original ZIP CNJ locators."""

import json
import zipfile

import pytest

from scripts.index_djen_originals import (
    extract_locations,
    load_index,
    merge_zip,
    save_index,
    shard_for,
)


def sample(tmp_path):
    path = tmp_path / "djen-2026-11-09-TJRO.zip"
    entries = [
        {"numero_processo": "70039901420268220022", "id": 1, "hash": "H1"},
        {"numero_processo": "70039901420268220022", "id": 2, "hash": "H2"},
        {"numero_processo": "08116865920268220000", "id": 3, "hash": "H3"},
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("TJRO-D-2026-11-09_1.json", json.dumps({"items": entries}))
    return path


def test_multiple_publications_preserved(tmp_path):
    path = sample(tmp_path)
    rows = extract_locations(path, item="djen-tjro-2026", filename=path.name)
    assert len(rows["70039901420268220022"]) == 2
    assert {r["hash"] for r in rows["70039901420268220022"]} == {"H1", "H2"}
    assert all(
        row["member"] == "TJRO-D-2026-11-09_1.json"
        for entries in rows.values()
        for row in entries
    )


def test_idempotent_update_and_replacement(tmp_path):
    path = sample(tmp_path)
    rows = extract_locations(path, item="djen-tjro-2026", filename=path.name)
    index = load_index(tmp_path / "index.json", item="djen-tjro-2026")
    assert merge_zip(index, filename=path.name, rows=rows)
    assert not merge_zip(index, filename=path.name, rows=rows)
    assert len(index["processos"]["70039901420268220022"]) == 2
    assert merge_zip(index, filename=path.name, rows={})
    assert not index["processos"]
    save_index(tmp_path / "index.json", index)
    assert load_index(tmp_path / "index.json", item="djen-tjro-2026") == index


def test_stable_sharding():
    cnj = "70039901420268220022"
    assert shard_for(cnj) == shard_for(cnj)
    assert len(shard_for(cnj)) == 2
    assert all(character in "0123456789abcdef" for character in shard_for(cnj))


def test_reject_bad_partition(tmp_path):
    path = tmp_path / "index.json"
    path.write_text('{"version":2,"item":"djen-tjsp-2026"}')
    with pytest.raises(ValueError):
        load_index(path, item="djen-tjro-2026")
