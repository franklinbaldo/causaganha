"""Test the dashboard data generation script."""

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock, patch


# Because the script has dashes in the name, we import it dynamically
script_path = Path("scripts/dashboard/generate-data.py")
spec = spec_from_file_location("generate_data", script_path)
generate_data = module_from_spec(spec)
sys.modules["generate_data"] = generate_data
spec.loader.exec_module(generate_data)


def test_generate_dashboard_data_includes_generated_at(tmp_path: Path) -> None:
    """Test that generate_dashboard_data includes a valid generated_at timestamp."""
    db_path = tmp_path / "causaganha.duckdb"
    output_path = tmp_path / "dashboard-data.json"

    with patch("generate_data.get_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_get_conn.return_value.con = mock_conn

        # Mock fetchone for stats
        mock_conn.execute.return_value.fetchone.return_value = (
            "2024-01-01",
            "2024-01-02",
            2,
            10,
        )
        # Mock fetchall for daily_stats, recent_activity, coverage_rows, velocity_rows
        mock_conn.execute.return_value.fetchall.return_value = []

        generate_data.generate_dashboard_data(db_path, output_path)

    assert output_path.exists()  # noqa: S101

    data = json.loads(output_path.read_text())
    assert "generated_at" in data  # noqa: S101

    # Check if generated_at is a valid ISO format string ending in Z
    generated_at = data["generated_at"]
    assert generated_at.endswith("Z")  # noqa: S101
    assert "T" in generated_at  # noqa: S101
