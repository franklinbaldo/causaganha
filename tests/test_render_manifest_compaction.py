"""Phase 2 tests for the manifest compactor (scripts/render_manifest_parquet.py).

The compactor's new contract (docs/planning/manifest-source-of-truth.md §4.3):
base = the current sync-manifest.parquet (CSV only as bootstrap fallback);
events = legacy upload-deltas + new manifest-log/ segments, merged
field-by-field last-write-wins by ``updated_at``; absorbed segments are
pruned (archived to manifest-log/compacted/, then deleted from manifest-log/)
only after the new base is safely uploaded.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Self

import duckdb


def _load_render_module():
    spec = importlib.util.spec_from_file_location(
        "render_manifest_parquet",
        Path(__file__).resolve().parents[1] / "scripts" / "render_manifest_parquet.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_base_parquet(path: Path, rows: list[tuple]) -> Path:
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE base (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR
        )
        """
    )
    con.executemany("INSERT INTO base VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.execute(f"COPY base TO '{path}' (FORMAT PARQUET)")
    con.close()
    return path


def _write_segment(path: Path, rows: list[tuple]) -> str:
    lines = ["tribunal,date,ia_status,djen_status,djen_raw,updated_at"]
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


BASE_ROWS = [
    # pending upload, verdict from 2024-02-01
    ("TJSP", "2024-01-02", None, "available", "200", "2024-02-01"),
    # unknown row
    ("TJRO", "2024-01-02", None, None, None, None),
    # already uploaded
    ("TJBA", "2024-01-02", "uploaded", "available", "200", "2024-01-15"),
]


def test_apply_segments_field_level_last_write_wins(tmp_path):
    rmp = _load_render_module()
    base = _make_base_parquet(tmp_path / "base.parquet", BASE_ROWS)

    seg1 = _write_segment(
        tmp_path / "20240301T000000Z-engine-1-aaaaaa.csv",
        [
            # newer than base → wins
            ("TJRO", "2024-01-02", "", "absent", "404", "2024-03-01"),
            # OLDER than base verdict (2024-02-01) → must NOT clobber
            ("TJSP", "2024-01-02", "", "absent", "404", "2024-01-01"),
        ],
    )
    seg2 = _write_segment(
        tmp_path / "20240302T000000Z-drain-2-bbbbbb.csv",
        [
            # uploaded-only event: sets ia_status without erasing djen fields
            ("TJSP", "2024-01-02", "uploaded", "", "", "2024-03-02"),
            # brand-new key → inserted
            ("TJMG", "2024-01-05", "", "confirmed", "200", "2024-03-02"),
        ],
    )

    con = duckdb.connect()
    assert rmp._load_base(con, base, None) == "parquet"
    uploaded, djen, inserted = rmp._apply_segments(con, [seg1, seg2])

    rows = {
        r[0]: (r[1], r[2], r[3])
        for r in con.execute(
            "SELECT tribunal, ia_status, djen_status, djen_raw FROM manifest"
        ).fetchall()
    }
    # TJRO: newer segment verdict applied
    assert rows["TJRO"] == (None, "absent", "404")
    # TJSP: old absent event LOST to the newer base verdict; uploaded event applied
    # without erasing the djen fields (empty = no change)
    assert rows["TJSP"] == ("uploaded", "available", "200")
    # TJBA untouched
    assert rows["TJBA"] == ("uploaded", "available", "200")
    # TJMG: inserted from segment
    assert rows["TJMG"] == (None, "confirmed", "200")
    assert (uploaded, djen, inserted) == (1, 1, 1)


def test_normalize_manifest_rewrites_contradictory_absent_200(tmp_path):
    rmp = _load_render_module()
    base = _make_base_parquet(
        tmp_path / "base.parquet",
        [
            ("TJSP", "2024-01-02", None, "absent", "200", "2024-02-01"),
            ("TJBA", "2024-01-02", None, "absent", "404", "2024-02-01"),
            ("TJRO", "2024-01-02", None, "available", "200", "2024-02-01"),
        ],
    )
    con = duckdb.connect()
    rmp._load_base(con, base, None)
    rmp._normalize_manifest(con)

    rows = dict(con.execute("SELECT tribunal, djen_raw FROM manifest").fetchall())
    assert rows["TJSP"] == "no_publications"  # absent+200 → sentinel
    assert rows["TJBA"] == "404"  # genuine absent untouched
    assert rows["TJRO"] == "200"  # available keeps its raw


def test_load_base_falls_back_to_csv_bootstrap(tmp_path):
    rmp = _load_render_module()
    csv = tmp_path / "sync-manifest.csv"
    csv.write_text(
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        "TJSP,2024-01-02,uploaded,available,200,2024-01-01\n",
        encoding="utf-8",
    )
    con = duckdb.connect()
    assert rmp._load_base(con, None, csv) == "csv"
    assert con.execute("SELECT count(*) FROM manifest").fetchone()[0] == 1


def test_merge_csv_lww_only_strictly_newer_rows_win(tmp_path):
    rmp = _load_render_module()
    base = _make_base_parquet(tmp_path / "base.parquet", BASE_ROWS)
    csv = tmp_path / "sync-manifest.csv"
    csv.write_text(
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        # STALE legacy row (older ts): the ~79K false-available case — must lose
        "TJSP,2024-01-02,,available,200,2024-01-20\n"
        # newer straggler from an in-flight old engine → wins
        "TJRO,2024-01-02,,absent,no_publications,2024-03-01\n"
        # equal ts → no-op (avoids re-flattening parquet refinements)
        "TJBA,2024-01-02,uploaded,available,200,2024-01-15\n"
        # row unknown to the base → inserted
        "TJMG,2024-01-08,,available,200,2024-03-01\n",
        encoding="utf-8",
    )

    con = duckdb.connect()
    rmp._load_base(con, base, csv)

    rows = {
        r[0]: (r[1], r[2], r[3], r[4])
        for r in con.execute(
            "SELECT tribunal, ia_status, djen_status, djen_raw, updated_at FROM manifest"
        ).fetchall()
    }
    assert rows["TJSP"][3] == "2024-02-01"  # stale CSV row did not win
    assert rows["TJRO"][1:3] == ("absent", "no_publications")  # newer straggler won
    assert rows["TJBA"] == ("uploaded", "available", "200", "2024-01-15")
    assert rows["TJMG"][1:3] == ("available", "200")  # inserted


def test_segment_and_delta_listing_filters():
    rmp = _load_render_module()
    names = [
        "sync-manifest.parquet",
        "sync-manifest.csv",
        "upload-deltas-111.csv",
        "upload-deltas-222.csv",
        "manifest-log/20240301T000000Z-engine-1-aaaaaa.csv",
        "manifest-log/compacted/20240201T000000Z-engine-0-bbbbbb.csv",
        "manifest-log/20240302T000000Z-probe-2-cccccc.csv",
        "somedir/upload-deltas-333.csv",  # not top-level → not a legacy delta
    ]
    assert rmp.fetch_delta_urls(names) == [
        f"{rmp.IA_DOWNLOAD_BASE}/upload-deltas-111.csv",
        f"{rmp.IA_DOWNLOAD_BASE}/upload-deltas-222.csv",
    ]
    assert rmp.fetch_segment_names(names) == [
        "manifest-log/20240301T000000Z-engine-1-aaaaaa.csv",
        "manifest-log/20240302T000000Z-probe-2-cccccc.csv",
    ]


class _FakeResp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeIAClient:
    """Records PUT/DELETE calls; can fail the archive copy for given names."""

    def __init__(self, fail_copy_for: set[str]) -> None:
        self.calls: list[tuple[str, str]] = []
        self._fail_copy_for = fail_copy_for

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def put(self, url: str, **_kwargs: object) -> _FakeResp:
        self.calls.append(("PUT", url))
        if any(name in url for name in self._fail_copy_for):
            return _FakeResp(503)
        return _FakeResp(200)

    async def delete(self, url: str) -> _FakeResp:
        self.calls.append(("DELETE", url))
        return _FakeResp(200)


def test_prune_segments_archives_then_deletes(tmp_path, monkeypatch):
    rmp = _load_render_module()
    monkeypatch.setenv("IAS3_ACCESS_KEY", "k")
    monkeypatch.setenv("IAS3_SECRET_KEY", "s")

    ok_local = tmp_path / "seg-ok.csv"
    ok_local.write_text("tribunal,date,ia_status,djen_status,djen_raw,updated_at\n")
    bad_local = tmp_path / "seg-bad.csv"
    bad_local.write_text("tribunal,date,ia_status,djen_status,djen_raw,updated_at\n")

    fake = _FakeIAClient(fail_copy_for={"seg-bad.csv"})
    monkeypatch.setattr(rmp, "create_upload_client", lambda _auth: fake)

    pruned = asyncio.run(
        rmp.prune_segments(
            [
                ("manifest-log/seg-ok.csv", ok_local),
                ("manifest-log/seg-bad.csv", bad_local),
            ]
        )
    )

    assert pruned == 1
    # copy to compacted/ happens BEFORE the delete of the original
    assert fake.calls[0] == ("PUT", f"{rmp.IA_S3_ITEM_URL}/manifest-log/compacted/seg-ok.csv")
    assert fake.calls[1] == ("DELETE", f"{rmp.IA_S3_ITEM_URL}/manifest-log/seg-ok.csv")
    # failed archive copy → original is NOT deleted (stays for the next run)
    assert ("DELETE", f"{rmp.IA_S3_ITEM_URL}/manifest-log/seg-bad.csv") not in fake.calls
