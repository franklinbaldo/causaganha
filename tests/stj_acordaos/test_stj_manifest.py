"""Tests for stj_acordaos.manifest — parse, serialization, roundtrip, counts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stj_acordaos.manifest import HEADER, ManifestSTJ


if TYPE_CHECKING:
    from pathlib import Path


def test_load_missing_file_returns_zero(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "nope.csv")
    assert manifest.load() == 0
    assert len(manifest) == 0


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "stj-manifest.csv"
    m1 = ManifestSTJ(path)
    m1.upsert("b.zip", "zip", "2024-01-31", "uploaded", 42)
    m1.upsert("a.json", "json", "2024-02-01", "", 7)
    m1.save()

    m2 = ManifestSTJ(path)
    assert m2.load() == 2
    rows = m2.to_df()
    # Sorted by arquivo
    assert [r["arquivo"] for r in rows] == ["a.json", "b.zip"]
    assert rows[0] == {
        "arquivo": "a.json",
        "tipo": "json",
        "data_extracao": "2024-02-01",
        "ia_status": "",
        "n_registros": 7,
        "updated_at": rows[0]["updated_at"],
    }
    assert rows[1]["ia_status"] == "uploaded"
    assert rows[1]["n_registros"] == 42


def test_saved_csv_has_header_and_one_line_per_entry(tmp_path: Path) -> None:
    path = tmp_path / "stj-manifest.csv"
    m = ManifestSTJ(path)
    m.upsert("a.json", "json", "2024-02-01", "", 1)
    m.save()

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER
    assert len(lines) == 2
    assert lines[1].startswith("a.json,json,2024-02-01,,1,")


def test_upsert_updates_existing_entry_and_stamps_updated_at(tmp_path: Path) -> None:
    m = ManifestSTJ(tmp_path / "m.csv")
    m.upsert("a.json", "json", "2024-01-01", "", 1)
    m.upsert("a.json", "json", "2024-01-02", "uploaded", 99)

    assert len(m) == 1
    row = m.to_df()[0]
    assert row["data_extracao"] == "2024-01-02"
    assert row["ia_status"] == "uploaded"
    assert row["n_registros"] == 99
    assert row["updated_at"]  # stamped, not empty


def test_load_skips_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    path.write_text(
        HEADER + "\n"
        "ok.zip,zip,2024-01-01,uploaded,10,2024-01-02T00:00:00+00:00\n"
        "short,row\n"  # fewer than 6 columns → skipped
        "\n"  # blank line → skipped
        "badcount.json,json,2024-01-01,,notanint,2024-01-02T00:00:00+00:00\n",
        encoding="utf-8",
    )
    m = ManifestSTJ(path)
    assert m.load() == 2
    by_name = {r["arquivo"]: r for r in m.to_df()}
    assert by_name["ok.zip"]["n_registros"] == 10
    # Unparseable count falls back to 0 instead of crashing
    assert by_name["badcount.json"]["n_registros"] == 0


def test_get_pending_uploads_excludes_uploaded(tmp_path: Path) -> None:
    m = ManifestSTJ(tmp_path / "m.csv")
    m.upsert("done.zip", "zip", "", "uploaded", 0)
    m.upsert("todo1.json", "json", "", "", 0)
    m.upsert("todo2.json", "json", "", "", 0)

    pending = m.get_pending_uploads()
    assert sorted(e.arquivo for e in pending) == ["todo1.json", "todo2.json"]
