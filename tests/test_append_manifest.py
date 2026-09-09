import tempfile
from pathlib import Path

import scripts.append_manifest as append_manifest


def test_get_new_uploads_preserves_comma_in_djen_raw(monkeypatch) -> None:
    """data/sync-manifest.csv is regenerated every run by DuckDB's own CSV
    writer (.github/actions/download-state), which quotes any field
    containing a comma per RFC4180 (e.g. djen_raw='network,timeout' is
    written as '"network,timeout"'). get_new_uploads() must parse that
    quoting correctly instead of a bare str.split(',') that would shift the
    downstream updated_at column and corrupt the published downloaded_at."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_file = Path(tmpdir) / "sync-manifest.csv"
        manifest_file.write_text(
            "tribunal,date,ia_status,djen_status,djen_raw,updated_at\n"
            'TJSP,2026-01-01,uploaded,absent,"network,timeout",2026-01-01T10:00:00Z\n'
        )
        monkeypatch.setattr(append_manifest, "SYNC_MANIFEST_PATH", manifest_file)

        rows = append_manifest.get_new_uploads()

        assert len(rows) == 1
        assert rows[0]["date"] == "2026-01-01"
        assert rows[0]["tribunal"] == "TJSP"
        assert rows[0]["downloaded_at"] == "2026-01-01T10:00:00Z"
