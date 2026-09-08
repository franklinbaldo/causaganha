"""Tests for scripts/generate_cache_from_manifest.py's status bucketing."""

from __future__ import annotations

from scripts.generate_cache_from_manifest import generate_calendar_json


def _row(*, ia_status: str = "", djen_status: str = "") -> dict[str, str]:
    return {
        "tribunal": "tjro",
        "date": "2026-09-01",
        "ia_status": ia_status,
        "djen_status": djen_status,
        "djen_raw": "",
        "updated_at": "",
    }


def test_calendar_day_buckets_sum_to_total() -> None:
    """Every row must land in exactly one of uploaded/pending/absent/unknown.

    Mirrors the djen_status vocabulary already canonicalized in
    web/src/queries/totals.qmd and tribunal_coverage.qmd: 'confirmed' and
    'available' are both pending (probe-verified, not yet uploaded), a bare
    'absent' is absent, and an empty djen_status (never checked) is unknown.
    """
    rows = [
        _row(ia_status="uploaded"),
        _row(djen_status="confirmed"),
        _row(djen_status="available"),
        _row(djen_status="absent"),
        _row(),
    ]

    result = generate_calendar_json(rows)

    assert len(result["days"]) == 1
    day = result["days"][0]
    assert day["total"] == 5
    assert day["uploaded"] == 1
    assert day["pending"] == 2
    assert day["absent"] == 1
    assert day["unknown"] == 1
    assert day["uploaded"] + day["pending"] + day["absent"] + day["unknown"] == day["total"]
