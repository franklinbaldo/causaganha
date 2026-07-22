from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from djen_backup.manifest import ManifestCounts, SyncManifest, interpret_djen_raw


FIXTURE = Path("tests/fixtures/manifest_contract_rows.csv")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        ("200", "available"),
        ("200:https://example.test/djen.zip", "available"),
        ("404", "absent"),
        ("400", "absent"),
        ("no_publications", "absent"),
        ("403", ""),
        ("500", ""),
        ("timeout", ""),
        ("network", ""),
    ],
)
def test_interpret_djen_raw_contract(raw: str, expected: str) -> None:
    assert interpret_djen_raw(raw) == expected


def test_manifest_fixture_load_counts_and_queries() -> None:
    manifest = SyncManifest()
    loaded = manifest.load_from_csv(FIXTURE.read_text(encoding="utf-8"), overwrite=True)

    assert loaded == 6
    assert manifest.counts() == ManifestCounts(
        total=6,
        uploaded=1,
        available=1,
        absent=2,
        unknown=2,
        ultima_atualizacao="2026-04-03T12:00:00+00:00",
    )
    assert manifest.has_uploaded_entries("tjsp", 2026) is True
    assert manifest.entries_needing_upload()

    transient = manifest.get_status("TJSP", date(2026, 4, 3))
    assert transient is not None
    assert transient.djen_raw == "403"
    assert transient.djen_status == ""


def test_absent_status_with_bare_200_raw_is_rewritten_to_no_publications() -> None:
    """Self-consistency guard (plan §5 Fase 1): an ``absent`` verdict paired
    with a bare ``200`` raw contradicts itself, since ``interpret_djen_raw``
    would otherwise re-derive ``200`` as ``available``. This is the exact
    bug class that produced ~79K false-available legacy rows — a checker
    that read only the HTTP 200 and never inspected the body.
    """
    manifest = SyncManifest()
    manifest.apply_event(
        "TJRO",
        date(2026, 4, 5),
        djen_status="absent",
        djen_raw="200",
        updated_at="2026-04-05T10:00:00+00:00",
    )

    entry = manifest.get_status("TJRO", date(2026, 4, 5))
    assert entry is not None
    assert entry.djen_raw == "no_publications"
    assert entry.djen_status == "absent"
    assert interpret_djen_raw(entry.djen_raw) == "absent"


def test_segment_merge_is_field_level_last_write_wins() -> None:
    manifest = SyncManifest()
    manifest.load_from_csv(FIXTURE.read_text(encoding="utf-8"), overwrite=True)

    segment = """tribunal,date,ia_status,djen_status,djen_raw,updated_at
TJSP,2026-04-03,,absent,404,2026-04-03T11:00:00+00:00
TJSP,2026-04-02,uploaded,,,2026-04-02T11:00:00+00:00
TJRO,2026-04-03,,confirmed,200,2026-04-03T14:00:00+00:00"""
    applied = manifest.apply_segment_csv(segment)

    assert applied == 3
    assert manifest.counts() == ManifestCounts(
        total=6,
        uploaded=2,
        available=2,
        absent=1,
        unknown=1,
        ultima_atualizacao="2026-04-03T14:00:00+00:00",
    )
    assert manifest.get_status("TJSP", date(2026, 4, 3)).djen_raw == "403"  # type: ignore[union-attr]
    assert manifest.get_status("TJSP", date(2026, 4, 2)).ia_status == "uploaded"  # type: ignore[union-attr]
    assert manifest.get_status("TJRO", date(2026, 4, 3)).djen_status == "available"  # type: ignore[union-attr]
