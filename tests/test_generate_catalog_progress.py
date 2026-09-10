from datetime import date

from scripts.generate_catalog import generate_consolidate_progress


def test_consolidate_progress_target_range_tracks_live_end_date() -> None:
    """target_range must track the caller's own notion of "today", not a frozen date.

    generate_collect_progress's target_end is `datetime.now(tz=UTC).date()` — live.
    generate_consolidate_progress must track the same kind of live boundary (passed
    in as end_date, matching generate_omission_stats's existing signature), not a
    date hardcoded at the time the function was written. A frozen target_end stops
    the window from growing while real consolidated dates keep accumulating past
    it, corrupting progress_pct for every day after the frozen date.
    """
    manifest = [
        {"file_type": "parquet", "date": "2026-06-15", "filename": "comunicacoes.parquet"},
    ]
    end_date = date(2026, 9, 10)

    result = generate_consolidate_progress(manifest, end_date)

    assert result["target_range"]["end"] == "2026-09-10"


def test_consolidate_progress_pct_stays_bounded_past_the_old_frozen_date() -> None:
    """A date well past the old hardcoded 2026-02-03 target_end must not corrupt progress_pct.

    Before the fix, any consolidated date after 2026-02-03 inflated unique_days
    while target_days stayed frozen at the 2024-01-01..2026-02-03 span, so
    progress_pct could exceed 100 for perfectly ordinary, fully-covered data.
    """
    target_start = date(2024, 1, 1)
    end_date = date(2026, 9, 10)
    manifest = [
        {"file_type": "parquet", "date": d.isoformat(), "filename": "comunicacoes.parquet"}
        for d in (
            date.fromordinal(o) for o in range(target_start.toordinal(), end_date.toordinal() + 1)
        )
    ]

    result = generate_consolidate_progress(manifest, end_date)

    assert result["progress_pct"] <= 100.0
