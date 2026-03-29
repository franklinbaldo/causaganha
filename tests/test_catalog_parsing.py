from datetime import date

from scripts.generate_catalog import (
    calculate_completed_items,
    is_complete,
    needs_listing,
    parse_filename,
)


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


def test_parse_filename_parquet() -> None:
    item_id = "djen-tjsp-2026"
    filename = "TJSP-2026-01-15-comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"


def test_parse_filename_parquet_legacy() -> None:
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
        item_id="djen-2026-01-01",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[],
        completed_items=set(),
    )
    assert should_list
    assert reason == "new_item"

    # 2. Recent date (< 7 days) -> True
    should_list, reason = needs_listing(
        item_id="djen-2026-01-05",
        item_date=date(2026, 1, 5),
        today=today,
        existing_files=[{"file_type": "zip"}],
        completed_items={"djen-2026-01-05"},
    )
    assert should_list
    assert reason == "recent_date"

    # 3. Already marked as complete (and not recent) -> False
    should_list, reason = needs_listing(
        item_id="djen-2026-01-01",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}, {"file_type": "parquet"}],
        completed_items={"djen-2026-01-01"},
    )
    assert not should_list
    assert reason == "already_complete"

    # 4. Lacks parquets but has zips -> True
    should_list, reason = needs_listing(
        item_id="djen-2026-01-01",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}],
        completed_items=set(),
    )
    assert should_list
    assert reason == "pending_consolidation"

    # 5. Not complete, has parquets -> True
    should_list, reason = needs_listing(
        item_id="djen-2026-01-01",
        item_date=date(2026, 1, 1),
        today=today,
        existing_files=[{"file_type": "zip"}, {"file_type": "parquet"}],
        completed_items=set(),
    )
    assert should_list
    assert reason == "not_complete"


def test_calculate_completed_items() -> None:
    manifest = [
        {"ia_item": "djen-2026-01-01", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-2026-01-01", "tribunal": "TJMG", "file_type": "zip"},
        {"ia_item": "djen-2026-01-01", "tribunal": "TRE-AC", "file_type": "absent"},
        {
            "ia_item": "djen-2026-01-01",
            "tribunal": "ALL",
            "file_type": "parquet",
        },  # Should be ignored for tribunal list
    ]

    # 3 unique tribunals in item, total=3 -> complete
    today = date(2026, 1, 15)
    res = calculate_completed_items(manifest, total_tribunals=3, today=today)

    assert "djen-2026-01-01" in res
    item_data = res["djen-2026-01-01"]

    assert item_data["tribunal_count"] == 2
    assert item_data["absent_count"] == 1

    assert item_data["tribunais_coletados"] == ["TJMG", "TJSP"]
    assert item_data["tribunais_ausentes"] == ["TRE-AC"]


def test_calculate_completed_items_incomplete() -> None:
    manifest = [
        {"ia_item": "djen-2026-01-01", "tribunal": "TJSP", "file_type": "zip"},
        {"ia_item": "djen-2026-01-01", "tribunal": "TJMG", "file_type": "zip"},
    ]

    # 2 unique tribunals in item, total=10 -> incomplete (20% < 80%)
    today = date(2026, 1, 15)
    res = calculate_completed_items(manifest, total_tribunals=10, today=today)

    assert "djen-2026-01-01" not in res


def test_calculate_completed_items_recent() -> None:
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
