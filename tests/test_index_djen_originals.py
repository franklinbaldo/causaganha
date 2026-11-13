"""Index ZIPs contain one CSV per CNJ and never duplicate DJEN texts."""

import zipfile
from pathlib import Path

from scripts.index_djen_originals import (
    apply_source,
    decode_csv,
    encode_csv,
    load_partition,
    partition_for,
    write_partition,
    index_item,
    remote_partition_name,
    short_cnj_filename,
    expand_cnj_filename,
)


def test_routing_from_cnj_is_filing_year_and_origin():
    assert partition_for("70726450920238220001") == "2023_0001.zip"
    assert partition_for("70039901420268220022") == "2026_0022.zip"


def test_csv_roundtrip_and_deduplication(tmp_path):
    cnj = "70726450920238220001"
    row = (
        "2026-11-09",
        "TJRO-D-2026-11-09_1.json",
        "778704990",
        "JKOdGxm7gYmLtXh1T7mM5lZy5DBkl2",
    )
    data = {cnj: [row, row]}
    path = tmp_path / "2023_0001.zip"
    write_partition(path, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == [f"{cnj[:9]}.csv"]
        raw = archive.read(f"{cnj[:9]}.csv")
        assert raw.startswith(b"data,membro,id,hash\n")
        assert decode_csv(raw) == [row]
    assert load_partition(path)[cnj] == [row]


def test_updates_only_publication_date_without_losing_history():
    cnj = "70726450920238220001"
    old = ("2026-11-09", "old.json", "1", "hash-1")
    unrelated = ("2026-11-10", "later.json", "2", "hash-2")
    replacement = ("2026-11-09", "new.json", "3", "hash-3")
    data = {cnj: [old, unrelated]}
    assert apply_source(
        data, publication_date="2026-11-09", new_rows={cnj: [replacement]}
    )
    assert sorted(data[cnj]) == sorted([replacement, unrelated])
    assert not apply_source(
        data, publication_date="2026-11-09", new_rows={cnj: [replacement]}
    )


def test_csv_roundtrip_unicode_and_commas():
    row = ("2026-11-09", "subfolder,1.json", "123", "hash")
    assert decode_csv(encode_csv([row])) == [row]


def test_ia_item_per_tribunal_and_filing_year():
    assert index_item("tjro", "2023") == "causaganha-2023-8-22"
    assert remote_partition_name("2023_0001.zip") == "0001.zip"


def test_cnj_filename_roundtrip_without_repeating_coordinates():
    cnj = "70726450920238220001"
    assert short_cnj_filename(cnj) == "707264509.csv"
    assert expand_cnj_filename("707264509.csv", Path("2023_0001.zip")) == cnj
