"""Test that incremental counts stay in sync with from-scratch recounts."""

from __future__ import annotations

from datetime import date

import pytest

from djen_backup.manifest import ManifestCounts, SyncManifest


def _recount(m: SyncManifest) -> ManifestCounts:
    """From-scratch recount via the slow path (force tally rebuild)."""
    m._counts_tally = None  # test inspects internal state to force rebuild
    return m.counts()


@pytest.mark.asyncio
async def test_incremental_counts_match_recount_after_marks() -> None:
    m = SyncManifest()
    m.build(["TJSP", "TJBA"], date(2024, 1, 1), date(2024, 1, 5))
    # Warm the tally so subsequent mark_* calls exercise the incremental path.
    initial = m.counts()
    assert initial.total == 10  # 2 tribunals x 5 weekdays
    assert initial.unknown == 10

    await m.mark_djen_raw("TJSP", date(2024, 1, 1), "200")
    await m.mark_djen_raw("TJSP", date(2024, 1, 2), "404")
    await m.mark_djen_raw("TJSP", date(2024, 1, 3), "403")  # transient → unknown
    await m.mark_uploaded("TJBA", date(2024, 1, 1))
    await m.mark_djen_raw("TJSP", date(2024, 1, 1), "200")  # idempotent

    incremental = m.counts()
    assert incremental == _recount(m)
    assert incremental.uploaded == 1
    assert incremental.available == 1
    assert incremental.absent == 1
    assert incremental.unknown == 7


@pytest.mark.asyncio
async def test_uploading_after_available_transitions_categories() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 1))
    m.counts()  # warm tally

    await m.mark_djen_raw("TJSP", date(2024, 1, 1), "200")
    assert m.counts().available == 1

    await m.mark_uploaded("TJSP", date(2024, 1, 1))
    c = m.counts()
    assert c.uploaded == 1
    assert c.available == 0
    assert c == _recount(m)


@pytest.mark.asyncio
async def test_has_uploaded_entries_incremental_after_marks() -> None:
    """The (tribunal, year) index updates incrementally on mark_*.

    Before this fix it was a binary cache rebuilt by O(N) scan; now it
    starts populated on first call and is maintained on every transition
    to ``uploaded`` so subsequent checks are O(1).
    """
    m = SyncManifest()
    m.build(["TJSP", "TJBA"], date(2024, 1, 1), date(2024, 1, 5))

    assert not m.has_uploaded_entries("TJSP", 2024)
    # Index is now warm (built lazily on the call above).

    await m.mark_uploaded("TJSP", date(2024, 1, 2))
    assert m.has_uploaded_entries("TJSP", 2024)
    assert not m.has_uploaded_entries("TJBA", 2024)

    await m.mark_ia_uploaded("TJBA", {date(2024, 1, 3), date(2024, 1, 4)})
    assert m.has_uploaded_entries("TJBA", 2024)
    # Idempotent re-mark must not corrupt the index.
    await m.mark_uploaded("TJSP", date(2024, 1, 2))
    assert m.has_uploaded_entries("TJSP", 2024)


@pytest.mark.asyncio
async def test_bulk_load_invalidates_tally() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))
    m.counts()  # warm tally

    csv = (
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        "TJSP,2024-01-01,uploaded,available,200,2024-01-02T00:00:00+00:00\n"
    )
    m.load_from_csv(csv, overwrite=True)
    assert m.counts() == _recount(m)
    assert m.counts().uploaded == 1
