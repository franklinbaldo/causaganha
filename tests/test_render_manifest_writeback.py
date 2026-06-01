"""Regression tests for the manifest compaction write-back (Phase 1).

See docs/planning/manifest-source-of-truth.md. The headline guarantee is that
the corrected CSV is *self-consistent*: a row the delta merge reclassified to
``absent`` while leaving ``djen_raw='200'`` must be rewritten so that re-deriving
the status from the raw still yields ``absent`` — never a phantom ``available``.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import duckdb

from djen_backup.manifest import interpret_djen_raw


def _load_render_module():
    spec = importlib.util.spec_from_file_location(
        "render_manifest_parquet",
        Path(__file__).resolve().parents[1] / "scripts" / "render_manifest_parquet.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_manifest(con):
    con.execute(
        """
        CREATE TABLE manifest (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR
        )
        """
    )
    con.execute(
        """
        INSERT INTO manifest VALUES
            ('TJSP', DATE '2024-01-02', '', 'available', '200', 'base'),
            ('TJRO', DATE '2024-01-02', '', '',          '',    'base'),
            ('TJBA', DATE '2024-01-02', '', 'available', '200', 'base'),
            ('TJMG', DATE '2024-01-02', '', 'available', '200', 'base')
        """
    )


def _write_delta(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tribunal", "date", "ia_status", "djen_status", "updated_at"])
        w.writerows(rows)
    return str(path)


def test_apply_deltas_is_set_based_and_keeps_uploaded_never_absent(tmp_path):
    import duckdb

    rmp = _load_render_module()
    con = duckdb.connect()
    _seed_manifest(con)

    # Two delta files for the same key (TJSP): one says uploaded, one says absent.
    # uploaded must win — an archived item is never also flagged absent.
    d1 = _write_delta(
        tmp_path / "upload-deltas-1.csv",
        [
            ("TJSP", "2024-01-02", "", "absent", "d1"),
            ("TJRO", "2024-01-02", "", "absent", "d1"),
        ],
    )
    d2 = _write_delta(
        tmp_path / "upload-deltas-2.csv",
        [
            ("TJSP", "2024-01-02", "uploaded", "", "d2"),
            ("TJBA", "2024-01-02", "uploaded", "", "d2"),
            ("TJMG", "2024-01-02", "", "confirmed", "d2"),
        ],
    )

    uploaded, absent, confirmed = rmp._apply_deltas(con, [d1, d2])

    rows = {
        r[0]: (r[1], r[2])
        for r in con.execute("SELECT tribunal, ia_status, djen_status FROM manifest").fetchall()
    }
    assert rows["TJSP"] == ("uploaded", "available")  # uploaded won; never absent
    assert rows["TJRO"] == ("", "absent")  # absent applied to a non-uploaded row
    assert rows["TJBA"] == ("uploaded", "available")  # uploaded only
    assert rows["TJMG"] == ("", "confirmed")  # available -> confirmed
    assert (uploaded, absent, confirmed) == (2, 1, 1)


def test_write_back_makes_absent_200_rows_self_consistent(tmp_path, monkeypatch):
    rmp = _load_render_module()
    out = tmp_path / "sync-manifest.csv"
    monkeypatch.setattr(rmp, "LOCAL_CSV", out)

    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE manifest (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR
        )
        """
    )
    con.execute(
        """
        INSERT INTO manifest VALUES
            -- the legacy bug: merge flipped status, raw still says 200
            ('TJSP', DATE '2024-01-02', '', 'absent', '200', '2024-01-03'),
            ('TJSP', DATE '2024-01-03', '', 'absent', '200:ok', '2024-01-04'),
            -- a genuine available must stay available
            ('TJRO', DATE '2024-01-02', 'uploaded', 'available', '200', '2024-01-03'),
            -- a real 404 absent is untouched
            ('TJBA', DATE '2024-01-02', '', 'absent', '404', '2024-01-03'),
            -- a probe-confirmed available: CSV must see plain 'available'
            ('TJMG', DATE '2024-01-02', '', 'confirmed', '200', '2024-01-03')
        """
    )

    rmp.write_back_csv(con)

    with out.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    by_key = {(r["tribunal"], r["date"]): r for r in rows}

    # Both absent-200 rows ("200" and "200:ok") are rewritten to the sentinel.
    assert by_key[("TJSP", "2024-01-02")]["djen_raw"] == "no_publications"
    assert by_key[("TJSP", "2024-01-03")]["djen_raw"] == "no_publications"
    # The available row keeps its raw; the genuine 404 absent is untouched.
    assert by_key[("TJRO", "2024-01-02")]["djen_raw"] == "200"
    assert by_key[("TJBA", "2024-01-02")]["djen_raw"] == "404"
    # 'confirmed' is normalized to 'available' so CSV consumers can upload it.
    assert by_key[("TJMG", "2024-01-02")]["djen_status"] == "available"
    assert by_key[("TJMG", "2024-01-02")]["djen_raw"] == "200"

    # Every written row re-derives consistently from its raw — no phantom available.
    for r in rows:
        derived = interpret_djen_raw(r["djen_raw"])
        if r["djen_status"] == "absent":
            assert derived == "absent", f"absent row has raw {r['djen_raw']!r} → {derived!r}"
        elif r["djen_status"] == "available":
            assert derived == "available"
