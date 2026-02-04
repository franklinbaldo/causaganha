"""Tests for generate_catalog.py logic."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import duckdb


# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from generate_catalog import generate_backfill_list, get_local_coverage


class TestGetLocalCoverage:
    """Tests for get_local_coverage function."""

    def test_get_local_coverage_success(self):
        """Should return set of (date, tribunal) strings."""
        mock_con = MagicMock(spec=duckdb.DuckDBPyConnection)
        # Mock result for fetchall
        # Return list of tuples: [(date_obj, 'TJSP'), (date_obj, 'TRF1')]
        # The query uses CAST(date AS VARCHAR), so DB returns strings actually.
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("2024-01-01", "TJSP"), ("2024-01-02", "TRF1")]
        mock_con.execute.return_value = mock_result

        result = get_local_coverage(mock_con)

        assert len(result) == 2
        assert ("2024-01-01", "TJSP") in result
        assert ("2024-01-02", "TRF1") in result

    def test_get_local_coverage_empty(self):
        """Should return empty set if table empty."""
        mock_con = MagicMock(spec=duckdb.DuckDBPyConnection)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_con.execute.return_value = mock_result

        result = get_local_coverage(mock_con)
        assert result == set()

    def test_get_local_coverage_table_missing(self):
        """Should return empty set if table missing (CatalogException)."""
        mock_con = MagicMock(spec=duckdb.DuckDBPyConnection)
        mock_con.execute.side_effect = duckdb.CatalogException("Table does not exist")

        result = get_local_coverage(mock_con)
        assert result == set()

    def test_get_local_coverage_generic_error(self):
        """Should return empty set on generic error."""
        mock_con = MagicMock(spec=duckdb.DuckDBPyConnection)
        mock_con.execute.side_effect = Exception("Some other error")

        result = get_local_coverage(mock_con)
        assert result == set()


class TestGenerateBackfillList:
    """Tests for generate_backfill_list logic."""

    def test_generate_backfill_list_no_local(self):
        """Should include all items if no local coverage and no manifest."""
        manifest = []
        start_date = date(2024, 1, 1)  # Monday
        end_date = date(2024, 1, 1)

        # 1 day * 96 courts = 96 items
        backfill = generate_backfill_list(manifest, start_date, end_date)

        # Just check count roughly or check one item
        assert len(backfill) == 96
        assert any(b["date"] == "2024-01-01" and b["tribunal"] == "TJSP" for b in backfill)

    def test_generate_backfill_list_with_local_exclusion(self):
        """Should exclude items present in local_coverage."""
        manifest = []
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 1)

        # Exclude TJSP locally
        local_coverage = {("2024-01-01", "TJSP")}

        backfill = generate_backfill_list(
            manifest, start_date, end_date, local_coverage=local_coverage
        )

        assert len(backfill) == 95  # 96 - 1
        assert not any(b["date"] == "2024-01-01" and b["tribunal"] == "TJSP" for b in backfill)
        assert any(b["date"] == "2024-01-01" and b["tribunal"] == "STF" for b in backfill)

    def test_generate_backfill_list_merges_manifest_and_local(self):
        """Should exclude items present in EITHER manifest OR local."""
        # Manifest has STF
        manifest = [{"date": "2024-01-01", "tribunal": "STF", "file_type": "zip"}]
        # Local has TJSP
        local_coverage = {("2024-01-01", "TJSP")}

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 1)

        backfill = generate_backfill_list(
            manifest, start_date, end_date, local_coverage=local_coverage
        )

        assert len(backfill) == 94  # 96 - 2
        assert not any(b["tribunal"] == "TJSP" for b in backfill)
        assert not any(b["tribunal"] == "STF" for b in backfill)
        assert any(b["tribunal"] == "TRF1" for b in backfill)
