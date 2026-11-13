"""Regression tests for the versioned minimal DJEN/DataJud index wire contract."""

import pytest

from causaganha.consolidate.process_pointer_pb import (
    decode_index,
    encode_index,
    update_datajud,
)

PUB = ("2026-11-09", "TJRO-D-2026-11-09_1.json", "778704990", "JKOdGxm7gYmLtXh1T7mM5lZy5DBkl2")


def locator(grau, updated="2026-11-09T12:00:00Z"):
    return {
        "tribunal": "TJRO",
        "grau": grau,
        "documento_id": f"TJRO_{grau}_70726450920238220001",
        "item_ia": "datajud-tjro",
        "arquivo_zip": "tjro_2026-11-09.zip",
        "membro": "70726450920238220001.json.gz",
        "atualizado_em": updated,
    }


def test_two_independent_datajud_grades_preserved():
    bytes_out = encode_index([PUB, PUB], [locator("G2"), locator("G1")])
    decoded = decode_index(bytes_out)
    assert decoded["publicacoes"] == [PUB]
    assert [item["grau"] for item in decoded["datajud"]] == ["G1", "G2"]
    assert encode_index(decoded["publicacoes"], decoded["datajud"]) == bytes_out


def test_datajud_only_index_roundtrip():
    encoded = encode_index([], [locator("G1")])
    assert decode_index(encoded) == {"publicacoes": [], "datajud": [locator("G1")]}


def test_unknown_version_and_truncation_rejected():
    with pytest.raises(ValueError):
        decode_index(b"")
    with pytest.raises(ValueError):
        decode_index(b"\x78\x02")
    with pytest.raises(ValueError):
        decode_index(b"\x0a\x7f")


def test_newer_datajud_only_replaces_matching_document():
    old = [locator("G1"), locator("G2")]
    changed = update_datajud(old, [locator("G1", "2026-11-10T12:00:00Z")])
    assert [entry["grau"] for entry in changed] == ["G1", "G2"]
    assert changed[0]["atualizado_em"] == "2026-11-10T12:00:00Z"
    assert update_datajud(changed, [locator("G1")]) == changed


def test_conflicting_equal_timestamp_is_rejected():
    old = locator("G1")
    new = {**old, "arquivo_zip": "different.zip"}
    with pytest.raises(ValueError, match="Conflicting"):
        update_datajud([old], [new])


def test_duplicate_datajud_identity_is_not_encoded_twice():
    with pytest.raises(ValueError):
        encode_index([], [locator("G1"), locator("G1")])
