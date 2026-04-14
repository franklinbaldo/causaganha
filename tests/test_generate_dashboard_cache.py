import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


script_path = Path("scripts/generate_dashboard_cache.py")
spec = spec_from_file_location("generate_dashboard_cache", script_path)
generate_dashboard_cache = module_from_spec(spec)
sys.modules.setdefault("duckdb", SimpleNamespace(DuckDBPyConnection=object))
sys.modules["generate_dashboard_cache"] = generate_dashboard_cache
assert spec.loader is not None
spec.loader.exec_module(generate_dashboard_cache)


def test_load_absent_coverage_from_ia_state_local_file(tmp_path: Path) -> None:
    """load_absent_coverage_from_ia_state reads djen_status=absent from sync-manifest.csv."""
    manifest_path = tmp_path / "sync-manifest.csv"
    manifest_path.write_text(
        "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
        "TJSP,2026-03-01,uploaded,absent,404,2026-03-01T10:00:00Z\n"
        "TJMG,2026-03-01,uploaded,available,200,2026-03-01T10:00:00Z\n"
        "TJSP,2026-03-02,uploaded,absent,404,2026-03-02T10:00:00Z\n"
        "TJRO,2026-03-02,uploaded,absent,404,2026-03-02T10:00:00Z\n",
        encoding="utf-8",
    )

    result = generate_dashboard_cache.load_absent_coverage_from_ia_state(manifest_path)

    assert set(result["TJSP"]) == {"2026-03-01", "2026-03-02"}
    assert result["TJRO"] == ["2026-03-02"]
    assert "TJMG" not in result


def test_load_absent_coverage_from_ia_state_missing_file(tmp_path: Path) -> None:
    """Missing sync-manifest.csv returns empty dict (no remote fallback)."""
    missing_path = tmp_path / "missing-sync-manifest.csv"
    result = generate_dashboard_cache.load_absent_coverage_from_ia_state(missing_path)
    assert result == {}
