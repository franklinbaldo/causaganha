import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


script_path = Path("scripts/generate_dashboard_cache.py")
spec = spec_from_file_location("generate_dashboard_cache", script_path)
generate_dashboard_cache = module_from_spec(spec)
sys.modules.setdefault("duckdb", SimpleNamespace(DuckDBPyConnection=object))
sys.modules["generate_dashboard_cache"] = generate_dashboard_cache
assert spec.loader is not None
spec.loader.exec_module(generate_dashboard_cache)


def test_load_absent_coverage_from_ia_state_local_file(tmp_path: Path) -> None:
    state_path = tmp_path / "ia-state.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 2,
                "entries": {
                    "2026-03-01": {"TJSP": "absent", "TJMG": "uploaded"},
                    "2026-03-02": {"TJSP": "absent", "TJRO": "absent"},
                },
            }
        ),
        encoding="utf-8",
    )

    result = generate_dashboard_cache.load_absent_coverage_from_ia_state(state_path)

    assert set(result["TJSP"]) == {"2026-03-01", "2026-03-02"}
    assert result["TJRO"] == ["2026-03-02"]
    assert "TJMG" not in result


def test_load_absent_coverage_from_ia_state_fallback_to_remote(tmp_path: Path) -> None:
    missing_state_path = tmp_path / "missing-ia-state.json"
    with patch("generate_dashboard_cache.fetch_json") as mock_fetch_json:
        mock_fetch_json.return_value = {
            "entries": {
                "2026-03-10": {"TRF1": "absent"},
                "2026-03-11": {"TRF1": "uploaded", "TRF2": "absent"},
            }
        }

        result = generate_dashboard_cache.load_absent_coverage_from_ia_state(missing_state_path)

    assert result == {"TRF1": ["2026-03-10"], "TRF2": ["2026-03-11"]}
