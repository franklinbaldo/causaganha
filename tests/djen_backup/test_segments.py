"""Phase 2 tests: manifest-log segment emission + parquet-base read path.

Covers dirty-only segment emission, unique immutable segment names, the
field-level last-write-wins merge (base + segments), the snapshot/restore
semantics of ``upload_segment_to_ia``, and the retry-then-give-up behavior
when the parquet base is unavailable — with no CSV fallback (Phase 3, see
docs/planning/manifest-source-of-truth.md §4/§5).
"""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

import duckdb
import pytest
import respx

from djen_backup.manifest import SyncManifest
from djen_backup.segments import (
    SEGMENT_HEADER,
    absent_raw_code,
    segment_name,
)


if TYPE_CHECKING:
    from pathlib import Path

DL = "https://archive.org/download/causaganha-dashboard"
S3 = "https://s3.us.archive.org/causaganha-dashboard"
META_FILES = "https://archive.org/metadata/causaganha-dashboard/files"


# ── Dirty tracking + segment emission ────────────────────────────────


@pytest.mark.asyncio
async def test_segment_contains_only_dirty_rows() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 3))
    assert m.dirty_count == 0  # build() is not an observation

    await m.mark_djen_raw("TJSP", date(2024, 1, 2), "404")

    lines = m.to_segment_csv().splitlines()
    assert lines[0] == SEGMENT_HEADER
    assert len(lines) == 2  # header + ONLY the mutated row
    assert lines[1].startswith("TJSP,2024-01-02,,absent,404,")


@pytest.mark.asyncio
async def test_loads_never_dirty_entries() -> None:
    m = SyncManifest()
    m.load_from_csv("TJSP,2024-01-02,,available,200,2024-01-01T00:00:00+00:00\n")
    m.apply_segment_csv("TJBA,2024-01-03,uploaded,,,2024-01-02T00:00:00+00:00\n")
    assert m.dirty_count == 0


def test_segment_name_is_unique_and_well_formed() -> None:
    a = segment_name("engine", "12345")
    b = segment_name("engine", "12345")
    assert a != b  # same writer + run + second → still no clobber
    assert re.fullmatch(r"\d{8}T\d{6}Z-engine-12345-[0-9a-f]{6}\.csv", a)


def test_absent_raw_code_never_records_bare_200() -> None:
    assert absent_raw_code(404) == "404"
    assert absent_raw_code(400) == "400"
    # HTTP 200 with "Sem comunicações" body → sentinel, not "200"
    assert absent_raw_code(200) == "no_publications"


# ── upload_segment_to_ia: snapshot / clear / restore ────────────────


@pytest.mark.asyncio
@respx.mock
async def test_upload_segment_clears_dirty_on_success() -> None:
    put = respx.put(url__startswith=f"{S3}/manifest-log/").respond(200)

    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))
    await m.mark_djen_raw("TJSP", date(2024, 1, 1), "no_publications")
    assert m.dirty_count == 1

    assert await m.upload_segment_to_ia("LOW k:s") is True
    assert m.dirty_count == 0

    body = put.calls.last.request.content.decode()
    assert body.splitlines()[0] == SEGMENT_HEADER
    assert len(body.splitlines()) == 2
    assert "TJSP,2024-01-01,,absent,no_publications," in body
    # Immutable segment path, unique name
    assert "/manifest-log/" in str(put.calls.last.request.url)


@pytest.mark.asyncio
@respx.mock
async def test_upload_segment_restores_dirty_on_failure() -> None:
    respx.put(url__startswith=f"{S3}/manifest-log/").respond(400)

    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))
    await m.mark_djen_raw("TJSP", date(2024, 1, 1), "404")

    assert await m.upload_segment_to_ia("LOW k:s") is False
    assert m.dirty_count == 1  # nothing lost — retried on the next flush


@pytest.mark.asyncio
async def test_upload_segment_noop_when_clean() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))
    # No dirty rows → returns True without any network call (respx not active
    # here: any HTTP attempt would raise).
    assert await m.upload_segment_to_ia("LOW k:s") is True


# ── Event merge: base + segments, field-level last-write-wins ───────


def test_apply_event_last_write_wins_by_updated_at() -> None:
    m = SyncManifest()
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="absent", djen_raw="404", updated_at="2024-02-01"
    )
    # Older event must NOT clobber the newer verdict
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="available", djen_raw="200", updated_at="2024-01-01"
    )
    e = m.get_status("TJSP", date(2024, 1, 2))
    assert e is not None
    assert (e.djen_status, e.djen_raw) == ("absent", "404")

    # Newer event wins
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="available", djen_raw="200", updated_at="2024-03-01"
    )
    e = m.get_status("TJSP", date(2024, 1, 2))
    assert (e.djen_status, e.djen_raw) == ("available", "200")


def test_apply_event_empty_fields_mean_no_change() -> None:
    m = SyncManifest()
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="available", djen_raw="200", updated_at="2024-01-01"
    )
    # A newer uploaded-only event must not erase the DJEN verdict
    m.apply_event("TJSP", date(2024, 1, 2), ia_status="uploaded", updated_at="2024-02-01")
    e = m.get_status("TJSP", date(2024, 1, 2))
    assert e.ia_status == "uploaded"
    assert (e.djen_status, e.djen_raw) == ("available", "200")


def test_apply_event_uploaded_is_monotonic() -> None:
    m = SyncManifest()
    m.apply_event("TJSP", date(2024, 1, 2), ia_status="uploaded", updated_at="2024-02-01")
    # An older full-row event without ia_status cannot revert a verified upload
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="available", djen_raw="200", updated_at="2024-01-01"
    )
    e = m.get_status("TJSP", date(2024, 1, 2))
    assert e.ia_status == "uploaded"


def test_apply_event_normalizes_confirmed_and_contradictory_absent() -> None:
    m = SyncManifest()
    # probe's 'confirmed' is a drain-only refinement — engine sees 'available'
    m.apply_event(
        "TJSP", date(2024, 1, 2), djen_status="confirmed", djen_raw="200", updated_at="2024-01-01"
    )
    assert m.get_status("TJSP", date(2024, 1, 2)).djen_status == "available"
    # absent + bare 200 raw contradicts itself → no_publications sentinel
    m.apply_event(
        "TJBA", date(2024, 1, 2), djen_status="absent", djen_raw="200", updated_at="2024-01-01"
    )
    e = m.get_status("TJBA", date(2024, 1, 2))
    assert (e.djen_status, e.djen_raw) == ("absent", "no_publications")


def test_apply_segment_csv_merges_rows() -> None:
    m = SyncManifest()
    m.load_from_csv("TJSP,2024-01-02,,available,200,2024-01-01T00:00:00+00:00\n")
    applied = m.apply_segment_csv(
        SEGMENT_HEADER + "\n"
        "TJSP,2024-01-02,uploaded,available,200,2024-01-05T00:00:00+00:00\n"
        "TJBA,2024-01-03,,absent,404,2024-01-05T00:00:00+00:00\n"
    )
    assert applied == 2
    assert m.get_status("TJSP", date(2024, 1, 2)).ia_status == "uploaded"
    assert m.get_status("TJBA", date(2024, 1, 3)).djen_status == "absent"


# ── load_from_ia: parquet base + segments, CSV fallback ─────────────


def _make_parquet(path: Path, rows: list[tuple]) -> bytes:
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE manifest (
            tribunal VARCHAR, date DATE, ia_status VARCHAR,
            djen_status VARCHAR, djen_raw VARCHAR, updated_at VARCHAR
        )
        """
    )
    con.executemany("INSERT INTO manifest VALUES (?, ?, ?, ?, ?, ?)", rows)
    con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    con.close()
    return path.read_bytes()


@pytest.mark.asyncio
@respx.mock
async def test_load_from_ia_merges_parquet_base_and_pending_segments(tmp_path: Path) -> None:
    parquet_bytes = _make_parquet(
        tmp_path / "base.parquet",
        [
            ("TJSP", "2024-01-02", None, "available", "200", "2024-01-01T00:00:00+00:00"),
            ("TJBA", "2024-01-02", "uploaded", None, None, "2024-01-01T00:00:00+00:00"),
            # legacy contradictory row in the base: absent but raw still 200
            ("TJMG", "2024-01-02", None, "absent", "200", "2024-01-01T00:00:00+00:00"),
        ],
    )
    respx.get(f"{DL}/sync-manifest.parquet").respond(200, content=parquet_bytes)
    respx.get(META_FILES).respond(
        200,
        json={
            "result": [
                {"name": "sync-manifest.parquet"},
                {"name": "manifest-log/20240105T000000Z-engine-1-aaaaaa.csv"},
                # already compacted — must NOT be replayed
                {"name": "manifest-log/compacted/20240101T000000Z-engine-0-bbbbbb.csv"},
            ]
        },
    )
    respx.get(f"{DL}/manifest-log/20240105T000000Z-engine-1-aaaaaa.csv").respond(
        200,
        text=(
            SEGMENT_HEADER + "\nTJSP,2024-01-02,uploaded,available,200,2024-01-05T00:00:00+00:00\n"
        ),
    )

    m = SyncManifest()
    await m.load_from_ia()

    assert len(m) == 3
    assert m.get_status("TJSP", date(2024, 1, 2)).ia_status == "uploaded"  # from segment
    assert m.get_status("TJBA", date(2024, 1, 2)).ia_status == "uploaded"  # from base
    e = m.get_status("TJMG", date(2024, 1, 2))
    # contradictory base row is normalized so it re-derives to absent
    assert (e.djen_status, e.djen_raw) == ("absent", "no_publications")


@pytest.mark.asyncio
@respx.mock
async def test_load_from_ia_gives_up_after_retries_without_touching_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase 3: no CSV fallback. All retries fail → return 0.

    The canonical CSV route is deliberately left unmocked — if the code ever
    reached for it, respx would raise for an unmocked route, which would
    fail this test. That absence of a mock IS the assertion that the CSV is
    never touched.
    """
    route = respx.get(f"{DL}/sync-manifest.parquet").respond(404)

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("djen_backup.manifest.asyncio.sleep", _no_sleep)

    m = SyncManifest()
    loaded = await m.load_from_ia()

    assert loaded == 0
    assert route.call_count == SyncManifest._LOAD_FROM_IA_RETRIES
