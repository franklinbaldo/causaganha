"""Tests for candidates.py — layout_revision gate and reconsolidation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causaganha.consolidate.candidates import (
    _load_consolidated_items,
    all_consolidated_dates,
    dates_at_current_version,
    dates_needing_reconsolidation,
)
from causaganha.consolidate.schema_registry import CURRENT_LAYOUT_REVISION, CURRENT_VERSION


def _write_manifest(tmp_path: Path, items: list[dict]) -> Path:
    manifest = {
        "schema_version": CURRENT_VERSION,
        "items": items,
        "generated_at": "2026-06-07T00:00:00+00:00",
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return str(path)


class TestLoadConsolidatedItems:
    def test_empty_when_file_missing(self, tmp_path: Path) -> None:
        result = _load_consolidated_items(str(tmp_path / "nope.json"))
        assert result == {}

    def test_reads_schema_version_and_layout_revision(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2026",
                "date": "2026-06-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2026-06-01T00:00:00+00:00",
            }
        ])
        items = _load_consolidated_items(path)
        assert items["2026-06-01"]["schema_version"] == CURRENT_VERSION
        assert items["2026-06-01"]["layout_revision"] == CURRENT_LAYOUT_REVISION

    def test_missing_layout_revision_defaults_to_empty_string(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2025",
                "date": "2025-01-01",
                "schema_version": CURRENT_VERSION,
                "tables": {},
                "consolidated_at": "2025-01-01T00:00:00+00:00",
            }
        ])
        items = _load_consolidated_items(path)
        assert items["2025-01-01"]["layout_revision"] == ""


class TestDatesAtCurrentVersion:
    def test_fully_current_item_is_included(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2026",
                "date": "2026-06-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2026-06-01T00:00:00+00:00",
            }
        ])
        assert "2026-06-01" in dates_at_current_version(path)

    def test_stale_layout_revision_is_excluded(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2025",
                "date": "2025-01-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": "",  # old item — no layout_revision recorded
                "tables": {},
                "consolidated_at": "2025-01-01T00:00:00+00:00",
            }
        ])
        assert "2025-01-01" not in dates_at_current_version(path)

    def test_stale_schema_version_is_excluded(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2024",
                "date": "2024-06-01",
                "schema_version": "2.0.0",
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2024-06-01T00:00:00+00:00",
            }
        ])
        assert "2024-06-01" not in dates_at_current_version(path)


class TestDatesNeedingReconsolidation:
    def test_stale_schema_version_is_returned(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2024",
                "date": "2024-06-01",
                "schema_version": "2.0.0",
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2024-06-01T00:00:00+00:00",
            }
        ])
        stale = dates_needing_reconsolidation(path)
        assert "2024-06-01" in stale

    def test_stale_layout_revision_is_returned(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2025",
                "date": "2025-01-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": "",  # old item — layout not yet applied
                "tables": {},
                "consolidated_at": "2025-01-01T00:00:00+00:00",
            }
        ])
        stale = dates_needing_reconsolidation(path)
        assert "2025-01-01" in stale

    def test_fully_current_item_is_excluded(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2026",
                "date": "2026-06-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2026-06-01T00:00:00+00:00",
            }
        ])
        stale = dates_needing_reconsolidation(path)
        assert "2026-06-01" not in stale

    def test_results_sorted_newest_first(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": f"djen-tjsp-{y}",
                "date": f"{y}-01-01",
                "schema_version": "2.0.0",
                "layout_revision": "",
                "tables": {},
                "consolidated_at": f"{y}-01-01T00:00:00+00:00",
            }
            for y in [2023, 2025, 2024]
        ])
        stale = dates_needing_reconsolidation(path)
        assert stale == sorted(stale, reverse=True)


class TestAllConsolidatedDates:
    def test_returns_current_and_stale_items(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, [
            {
                "item_id": "djen-tjsp-2026",
                "date": "2026-06-01",
                "schema_version": CURRENT_VERSION,
                "layout_revision": CURRENT_LAYOUT_REVISION,
                "tables": {},
                "consolidated_at": "2026-06-01T00:00:00+00:00",
            },
            {
                "item_id": "djen-tjsp-2025",
                "date": "2025-01-01",
                "schema_version": "2.0.0",
                "layout_revision": "",
                "tables": {},
                "consolidated_at": "2025-01-01T00:00:00+00:00",
            },
        ])
        dates = all_consolidated_dates(path)
        assert "2026-06-01" in dates
        assert "2025-01-01" in dates
        assert dates == sorted(dates, reverse=True)

    def test_empty_when_no_manifest(self, tmp_path: Path) -> None:
        assert all_consolidated_dates(str(tmp_path / "nope.json")) == []
