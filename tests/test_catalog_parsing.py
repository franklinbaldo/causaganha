import tempfile
from datetime import date
from pathlib import Path

from scripts.generate_catalog import (
    calculate_completed_items,
    get_items_from_sync_manifest,
    is_complete,
    needs_listing,
    parse_filename,
)


def test_get_items_from_sync_manifest() -> None:
    # 1. Missing file
    res = get_items_from_sync_manifest(Path("non_existent_sync_manifest.csv"))
    assert res == []

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_file = Path(tmpdir) / "sync-manifest.csv"

        # 2. Valid CSV with multiple uploaded entries across tribunals/years
        manifest_file.write_text(
            "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
            "TJSP,2026-01-01,uploaded,available,200,2026-01-01T10:00:00Z\n"
            "TJMG,2026-01-02,uploaded,available,200,2026-01-02T10:00:00Z\n"
            "TJRO,2025-12-31,uploaded,available,200,2025-12-31T10:00:00Z\n"
        )
        res = get_items_from_sync_manifest(manifest_file)
        assert sorted(res) == ["djen-tjmg-2026", "djen-tjro-2025", "djen-tjsp-2026"]

        # 3. Only non-uploaded entries → empty
        manifest_file.write_text(
            "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
            "TJSP,2026-01-01,pending,available,200,2026-01-01T10:00:00Z\n"
        )
        res = get_items_from_sync_manifest(manifest_file)
        assert res == []

        # 4. Empty file (header only) → empty
        manifest_file.write_text("tribunal,date,ia_status,djen_status,djen_raw,updated_at\n")
        res = get_items_from_sync_manifest(manifest_file)
        assert res == []


def test_parse_filename_zip() -> None:
    item_id = "djen-tjsp-2026"
    filename = "djen-2026-01-15-TJSP.zip"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "zip"


def test_parse_filename_absent() -> None:
    item_id = "djen-tre-ac-2026"
    filename = "djen-2026-01-15-TRE-AC.absent"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TRE-AC"
    assert res["file_type"] == "absent"


def test_parse_filename_root_parquet_tribunal_year() -> None:
    """Root parquets (comunicacoes.parquet) in tribunal-year items."""
    item_id = "djen-tjro-2025"
    filename = "comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] is None
    assert res["tribunal"] == "TJRO"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"


def test_parse_filename_root_parquet_compound_tribunal() -> None:
    """Root parquets in items with compound tribunal codes (TRE-AC)."""
    item_id = "djen-tre-ac-2026"
    filename = "textos.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] is None
    assert res["tribunal"] == "TRE-AC"
    assert res["table_name"] == "textos"


def test_parse_filename_marker_tribunal_year() -> None:
    """_consolidated.marker in tribunal-year items."""
    item_id = "djen-tjsp-2026"
    filename = "_consolidated.marker"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] is None
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "marker"


def test_parse_filename_parquet() -> None:
    item_id = "djen-tjsp-2026"
    filename = "TJSP-2026-01-15-comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"


def test_parse_filename_parquet_legacy_item() -> None:
    # Tests backward compat with old items still on IA (djen-YYYY-MM-DD format)
    item_id = "djen-2026-01-15"
    filename = "djen-2026-01-15-TJSP-comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"


def test_is_complete() -> None:
    # Simulate total tribunals = 10
    total = 10

    # 0 tribunals present
    assert not is_complete([], total)

    # 7 tribunals present (< 80%)
    files = [{"tribunal": f"T{i}", "file_type": "zip"} for i in range(7)]
    assert not is_complete(files, total)

    # 8 tribunals present (>= 80%)
    files = [{"tribunal": f"T{i}", "file_type": "zip"} for i in range(8)]
    assert is_complete(files, total)

    # Mix of zips and absents for 8 unique tribunals
    files = [
        {"tribunal": f"T{i}", "file_type": "zip" if i % 2 == 0 else "absent"} for i in range(8)
    ]
    assert is_complete(files, total)

    # Ignore parquets in count
    files = [{"tribunal": f"T{i}", "file_type": "parquet"} for i in range(8)]
    assert not is_complete(files, total)

    # Multiple files for same tribunal shouldn't double count
    files = [
        {"tribunal": "T1", "file_type": "zip"},
        {"tribunal": "T1", "file_type": "absent"},
        {"tribunal": "T2", "file_type": "zip"},
    ]
    # For total=2, 80% is 1.6 tribunals (needs 2).
    assert is_complete(files, 2)


def test_needs_listing() -> None:
    today = date(2026, 1, 10)

    # 1. No existing files -> True
    should_list, reason = needs_listing(
        item_id="djen-tjsp-2026",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[],
        completed_items=set(),
    )
    assert should_list
    assert reason == "new_item"

    # 2. Recent date (< 7 days) -> True
    should_list, reason = needs_listing(
        item_id="djen-tjsp-2026",
        item_date=date(2026, 1, 5),
        today=today,
        existing_files=[{"file_type": "zip"}],
        completed_items={"djen-tjsp-2026"},
    )
    assert should_list
    assert reason == "recent_date"

    # 3. Already marked as complete (and not recent) -> False
    should_list, reason = needs_listing(
        item_id="djen-tjsp-2026",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}, {"file_type": "parquet"}],
        completed_items={"djen-tjsp-2026"},
    )
    assert not should_list
    assert reason == "already_complete"

    # 4. Lacks parquets but has zips -> True
    should_list, reason = needs_listing(
        item_id="djen-tjsp-2026",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}],
        completed_items=set(),
    )
    assert should_list
    assert reason == "pending_consolidation"

    # 5. Not complete, has parquets -> True
    should_list, reason = needs_listing(
        item_id="djen-tjsp-2026",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}, {"file_type": "parquet"}],
        completed_items=set(),
    )
    assert should_list
    assert reason == "not_complete"


def test_calculate_completed_items() -> None:
    manifest = [
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJMG", "file_type": "zip"},
        {"ia_item": "djen-tjsp-2026", "tribunal": "TRE-AC", "file_type": "absent"},
        {
            "ia_item": "djen-tjsp-2026",
            "tribunal": "ALL",
            "file_type": "parquet",
        },  # Should be ignored for tribunal list
    ]

    # 3 unique tribunals in item, total=3 -> complete
    today = date(2026, 1, 15)
    res = calculate_completed_items(manifest, total_tribunals=3, today=today)

    assert "djen-tjsp-2026" in res
    item_data = res["djen-tjsp-2026"]

    assert item_data["tribunal_count"] == 2
    assert item_data["absent_count"] == 1

    assert item_data["tribunais_coletados"] == ["TJMG", "TJSP"]
    assert item_data["tribunais_ausentes"] == ["TRE-AC"]


def test_calculate_completed_items_incomplete() -> None:
    manifest = [
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJMG", "file_type": "zip"},
    ]

    # 2 unique tribunals in item, total=10 -> incomplete (20% < 80%)
    today = date(2026, 1, 15)
    res = calculate_completed_items(manifest, total_tribunals=10, today=today)

    assert "djen-tjsp-2026" not in res


def test_calculate_completed_items_recent_legacy_format() -> None:
    # Recency filtering only works with legacy item IDs (djen-YYYY-MM-DD)
    # because get_item_date() extracts the date from the ID.
    manifest = [
        {"ia_item": "djen-2026-01-01", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-2026-01-01", "tribunal": "TJMG", "file_type": "zip"},
        {"ia_item": "djen-2026-01-01", "tribunal": "TRE-AC", "file_type": "absent"},
    ]

    # Item is from Jan 1st, but 'today' is Jan 5th (only 4 days old).
    # Even though it has enough tribunals (3/3), it shouldn't be considered complete yet.
    today = date(2026, 1, 5)
    res = calculate_completed_items(manifest, total_tribunals=3, today=today)

    assert "djen-2026-01-01" not in res


def test_calculate_completed_items_new_format_no_recency() -> None:
    # New tribunal-year format (djen-{tribunal}-{year}) has no embedded date,
    # so get_item_date() returns None and the recency filter is skipped.
    # The item should be marked complete if it meets the threshold.
    manifest = [
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-tjsp-2026", "tribunal": "TJMG", "file_type": "zip"},
        {"ia_item": "djen-tjsp-2026", "tribunal": "TRE-AC", "file_type": "absent"},
    ]

    today = date(2026, 1, 5)
    res = calculate_completed_items(manifest, total_tribunals=3, today=today)

    assert "djen-tjsp-2026" in res
